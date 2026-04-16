"""新闻分析图的节点函数。

每个节点是一个异步函数，接收当前状态并返回更新。
"""

from langchain_core.messages import HumanMessage

from tasks.task2_analyze_flow.models import (
    InvestmentValueOutput,
    RecommendationOutput,
    TokenExtractionOutput,
)
from tasks.task2_analyze_flow.prompts import (
    format_investment_value_prompt,
    format_neutral_recommendation_prompt,
    format_recommendation_prompt,
    format_token_extraction_prompt,
    format_trend_analysis_prompt,
)
from tasks.task2_analyze_flow.state import GraphState
from app.wrappers.llm import call_llm_structured, get_llm
from app.data.logger import create_logger

logger = create_logger("分析流水线::node")


async def investment_value_node(state: GraphState) -> dict:
    """节点 1：投资价值判断

    分析快讯是否具有投资价值（利好/利空/无关），输出判断结果和置信度
    """
    logger.info(f"节点: 投资价值判断，新闻 {state['news_id']}")

    llm = get_llm()
    prompt = format_investment_value_prompt(state["title"], state["content"])

    # DeepSeek 的 JSON schema
    schema = {
        "type": "object",
        "properties": {
            "value": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string"},
        },
        "required": ["value", "confidence", "reasoning"],
    }

    try:
        response = await call_llm_structured(llm, prompt, InvestmentValueOutput, schema)

        # 判断是否继续进行完整分析
        should_continue = response.value != "neutral" or response.confidence >= 0.5

        return {
            "investment_value": response.value,
            "investment_confidence": response.confidence,
            "investment_reasoning": response.reasoning,
            "should_continue": should_continue,
        }
    except Exception as e:
        logger.error(f"投资价值判断节点出错: {e}")
        return {
            "investment_value": "neutral",
            "investment_confidence": 0.0,
            "investment_reasoning": f"Analysis failed: {str(e)}",
            "should_continue": False,
            "error": str(e),
        }


async def extract_tokens_node(state: GraphState) -> dict:
    """节点 2：代币提取

    从有价值的快讯中提取相关代币（名称、符号），如果无关联代币则标记为无
    """
    logger.info(f"节点: 代币提取，新闻 {state['news_id']}")

    llm = get_llm()
    prompt = format_token_extraction_prompt(state["title"], state["content"])

    # DeepSeek 的 JSON schema
    schema = {
        "type": "object",
        "properties": {
            "tokens": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "name": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["symbol", "name", "confidence"],
                },
            }
        },
        "required": ["tokens"],
    }

    try:
        response = await call_llm_structured(llm, prompt, TokenExtractionOutput, schema)

        tokens = [t.model_dump() if hasattr(t, "model_dump") else t for t in response.tokens]
        logger.info(f"提取到 {len(tokens)} 个代币: {[t.get('symbol') for t in tokens]}")

        return {"tokens": tokens}
    except Exception as e:
        logger.error(f"代币提取节点出错: {e}")
        return {"tokens": [], "error": str(e)}


async def search_token_info_node(state: GraphState) -> dict:
    """节点 3：代币信息搜索

    对提取到的代币搜索（CMC/GeckoTerminal等接口）补充市场信息（当前价格、市值等）
    """
    logger.info(f"节点: 代币信息搜索，新闻 {state['news_id']}")

    tokens = state.get("tokens") or []

    if not tokens:
        return {"token_details": {}}

    try:
        from app.wrappers.cmc import CMCClient

        cmc = CMCClient()
        token_details = {}

        for token in tokens:
            symbol = token.get("symbol") if isinstance(token, dict) else token.symbol
            try:
                info = await cmc.get_token_info(symbol)
                if info:
                    token_details[symbol] = info
            except Exception as e:
                logger.warning(f"获取 {symbol} 信息失败: {e}")
                # 继续处理其他代币

        logger.info(f"已获取 {len(token_details)} 个代币的市场数据")
        return {"token_details": token_details}
    except ImportError:
        logger.warning("CMC 客户端不可用，跳过代币信息搜索")
        return {"token_details": {}}
    except Exception as e:
        logger.error(f"代币信息搜索节点出错: {e}")
        return {"token_details": {}, "error": str(e)}


async def rag_knowledge_node(state: GraphState) -> dict:
    """节点 3.5：从 RAG 知识库检索相关知识。

    使用知识库中的 Web3 领域知识增强分析。
    """
    logger.info(f"节点: RAG 知识检索，新闻 {state['news_id']}")

    tokens = state.get("tokens") or []
    title = state.get("title", "")
    content = state.get("content", "")

    # 从新闻内容构建搜索查询
    query = f"{title}. {content[:500]}"  # 取前 500 字符作为上下文

    # 提取代币符号用于过滤
    token_symbols = []
    if tokens:
        token_symbols = [
            t.get("symbol") if isinstance(t, dict) else t.symbol
            for t in tokens
        ]

    try:
        from app.rag.chain import get_rag_chain

        rag = get_rag_chain(top_k=3, threshold=0.6)

        # 如有代币符号则按代币过滤查询
        result = await rag.query(
            query,
            filter_tokens=token_symbols if token_symbols else None,
        )

        rag_context = result.get("answer", "")
        sources = result.get("sources", [])

        logger.info(f"RAG 检索到 {len(sources)} 个片段，上下文长度: {len(rag_context)}")

        return {
            "rag_context": rag_context,
            "rag_sources": sources,
        }

    except ImportError:
        logger.warning("RAG 链不可用")
        return {"rag_context": None, "rag_sources": []}
    except Exception as e:
        logger.error(f"RAG 知识检索节点出错: {e}")
        return {"rag_context": None, "rag_sources": [], "error": str(e)}


async def kg_knowledge_node(state: GraphState) -> dict:
    """节点 3.6：从知识图谱检索实体关系。

    使用 Neo4j 中的实体关系数据增强分析。
    """
    logger.info(f"节点: 知识图谱检索，新闻 {state['news_id']}")

    tokens = state.get("tokens") or []
    title = state.get("title", "")
    content = state.get("content", "")

    try:
        from app.kg.client import Neo4jClient
        from app.kg.query import GraphQuery

        # 创建 Neo4j 客户端
        client = Neo4jClient()
        await client.connect()

        try:
            query_service = GraphQuery(client)

            # 搜索新闻中提到的项目
            kg_context_parts = []

            # 从标题/内容中提取项目名称（简单启发式）
            # 生产环境中应使用 NER 或 LLM 提取
            project_keywords = set()

            # 将代币符号添加为潜在项目
            for token in tokens:
                symbol = token.get("symbol") if isinstance(token, dict) else token.symbol
                project_keywords.add(symbol)

            # 从标题中按关键词搜索项目
            words = set(title.lower().split() + content.lower()[:200].split())
            for word in words:
                if len(word) > 3:  # 过滤短词
                    project_keywords.add(word.capitalize())

            # 为每个潜在项目查询知识图谱
            kg_entities = {"projects": [], "tokens": [], "relationships": []}

            for keyword in list(project_keywords)[:5]:  # 限制最多 5 次搜索
                # 搜索项目
                projects = await query_service.search_projects_by_keyword(keyword, limit=3)
                for project in projects:
                    if project not in kg_entities["projects"]:
                        kg_entities["projects"].append(project)

                        # 获取相关实体
                        context = await query_service.get_project_context(project.get("name", ""))
                        if context:
                            kg_entities["tokens"].extend(context.get("tokens", []))
                            kg_entities["relationships"].extend(context.get("team", []))
                            kg_entities["relationships"].extend(context.get("investors", []))

            # 将 KG 上下文格式化供 LLM 使用
            if kg_entities["projects"]:
                kg_context_parts.append(f"## Related Projects ({len(kg_entities['projects'])})")
                for proj in kg_entities["projects"][:5]:
                    kg_context_parts.append(f"- {proj.get('name', 'Unknown')}: {proj.get('description', 'No description')[:100]}")

            if kg_entities["tokens"]:
                kg_context_parts.append(f"\n## Related Tokens ({len(kg_entities['tokens'])})")
                for token in kg_entities["tokens"][:5]:
                    kg_context_parts.append(f"- {token.get('symbol', 'Unknown')}: {token.get('name', 'Unknown')}")

            if kg_entities["relationships"]:
                kg_context_parts.append(f"\n## Entity Relationships ({len(kg_entities['relationships'])})")
                for rel in kg_entities["relationships"][:5]:
                    if "person" in rel:
                        kg_context_parts.append(f"- Person: {rel['person'].get('name', 'Unknown')} ({rel.get('role', 'Unknown')})")
                    elif "institution" in rel:
                        inst = rel["institution"]
                        kg_context_parts.append(f"- Investor: {inst.get('name', 'Unknown')} ({rel.get('round_type', 'Unknown')})")

            kg_context = "\n".join(kg_context_parts) if kg_context_parts else ""
            logger.info(f"知识图谱检索到 {len(kg_entities['projects'])} 个项目，上下文长度: {len(kg_context)}")

            return {
                "kg_context": kg_context,
                "kg_entities": kg_entities,
            }

        finally:
            await client.close()

    except ImportError:
        logger.warning("知识图谱模块不可用")
        return {"kg_context": None, "kg_entities": {}}
    except Exception as e:
        logger.error(f"知识图谱检索节点出错: {e}")
        return {"kg_context": None, "kg_entities": {}, "error": str(e)}


async def trend_analysis_node(state: GraphState) -> dict:
    """节点 4：涨跌分析

    结合 新闻内容 和 市场信息、RAG知识、KG知识图谱 分析代币短期涨跌趋势
    """
    logger.info(f"节点: 涨跌分析，新闻 {state['news_id']}")

    llm = get_llm()

    # 格式化代币数据用于提示词
    token_details = state.get("token_details") or {}
    token_data_str = "\n".join(
        f"- {symbol}: ${data.get('price', 'N/A')} "
        f"(24h: {data.get('change_24h', 'N/A')}%, "
        f"MCap: ${data.get('market_cap', 'N/A')})"
        for symbol, data in token_details.items()
    )
    if not token_data_str:
        token_data_str = "No token market data available"

    # 获取 RAG 上下文（如有）
    rag_context = state.get("rag_context")
    if rag_context:
        logger.info(f"使用 RAG 上下文（长度: {len(rag_context)}）")

    # 获取 KG 上下文（如有）
    kg_context = state.get("kg_context")
    if kg_context:
        logger.info(f"使用知识图谱上下文（长度: {len(kg_context)}）")

    # 合并 RAG 和 KG 上下文
    enhanced_context = ""
    if rag_context:
        enhanced_context += f"\n## RAG Knowledge\n{rag_context}"
    if kg_context:
        enhanced_context += f"\n## Knowledge Graph Entities\n{kg_context}"

    prompt = format_trend_analysis_prompt(
        title=state["title"],
        content=state["content"],
        investment_value=state.get("investment_value", "unknown"),
        confidence=state.get("investment_confidence", 0.0),
        token_data=token_data_str,
        rag_context=enhanced_context if enhanced_context else None,
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        trend_text = response.content.strip() if hasattr(response, "content") else str(response)

        return {"trend_analysis": trend_text}
    except Exception as e:
        logger.error(f"涨跌分析节点出错: {e}")
        return {"trend_analysis": "", "error": str(e)}


async def generate_recommendation_node(state: GraphState) -> dict:
    """节点 5：生成最终的交易建议

    给出 买入/卖出/观望 建议和风险等级
    """
    logger.info(f"节点: 生成交易建议，新闻 {state['news_id']}")

    llm = get_llm()

    # DeepSeek 的 JSON schema
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["buy", "sell", "hold"]},
            "reasoning": {"type": "string"},
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["action", "reasoning", "risk_level"],
    }

    # 如果跳过了分析，使用中性提示词
    if not state.get("should_continue", True):
        prompt = format_neutral_recommendation_prompt(state["title"], state["content"])
        try:
            response = await call_llm_structured(llm, prompt, RecommendationOutput, schema)
            return {
                "recommendation": response.action,
                "risk_level": response.risk_level,
                "recommendation_reasoning": response.reasoning,
            }
        except Exception as e:
            logger.error(f"生成交易建议节点出错: {e}")
            return {
                "recommendation": "hold",
                "risk_level": "low",
                "recommendation_reasoning": f"Analysis error: {str(e)}",
            }
    else:
        prompt = format_recommendation_prompt(
            title=state["title"],
            investment_value=state.get("investment_value", "neutral"),
            confidence=state.get("investment_confidence", 0.0),
            trend_analysis=state.get("trend_analysis", ""),
        )

        try:
            response = await call_llm_structured(llm, prompt, RecommendationOutput, schema)
            return {
                "recommendation": response.action,
                "risk_level": response.risk_level,
                "recommendation_reasoning": response.reasoning,
            }
        except Exception as e:
            logger.error(f"生成交易建议节点出错: {e}")
            return {
                "recommendation": "hold",
                "risk_level": "low",
                "recommendation_reasoning": f"Analysis error: {str(e)}",
            }


def should_continue_route(state: GraphState) -> str:
    """路由函数：决定是否继续进行完整分析。

    Returns:
        "continue": 继续代币提取和完整分析
        "skip": 跳转到最终建议（针对中性新闻）
    """
    if state.get("should_continue", True):
        return "continue"
    return "skip"
