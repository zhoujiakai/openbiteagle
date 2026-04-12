"""Node functions for the news analysis graph.

Each node is an async function that takes the current state and returns updates.
"""

import logging

from langchain_core.messages import HumanMessage

from app.graph.news_analysis.models import (
    InvestmentValueOutput,
    RecommendationOutput,
    TokenExtractionOutput,
)
from app.graph.news_analysis.prompts import (
    format_investment_value_prompt,
    format_neutral_recommendation_prompt,
    format_recommendation_prompt,
    format_token_extraction_prompt,
    format_trend_analysis_prompt,
)
from app.graph.news_analysis.state import GraphState
from app.wrappers.llm import call_llm_structured, get_llm

logger = logging.getLogger(__name__)


async def investment_value_node(state: GraphState) -> dict:
    """Node 1: Judge investment value of the news.

    Determines if the news has bullish, bearish, or neutral investment value.
    """
    logger.info(f"Node: investment_value for news {state['news_id']}")

    llm = get_llm()
    prompt = format_investment_value_prompt(state["title"], state["content"])

    # JSON schema for DeepSeek
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

        # Determine if we should continue with full analysis
        should_continue = response.value != "neutral" or response.confidence >= 0.5

        return {
            "investment_value": response.value,
            "investment_confidence": response.confidence,
            "investment_reasoning": response.reasoning,
            "should_continue": should_continue,
        }
    except Exception as e:
        logger.error(f"Error in investment_value_node: {e}")
        return {
            "investment_value": "neutral",
            "investment_confidence": 0.0,
            "investment_reasoning": f"Analysis failed: {str(e)}",
            "should_continue": False,
            "error": str(e),
        }


async def extract_tokens_node(state: GraphState) -> dict:
    """Node 2: Extract cryptocurrency tokens from the news.

    Identifies tokens mentioned in the content.
    """
    logger.info(f"Node: extract_tokens for news {state['news_id']}")

    llm = get_llm()
    prompt = format_token_extraction_prompt(state["title"], state["content"])

    # JSON schema for DeepSeek
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
        logger.info(f"Extracted {len(tokens)} tokens: {[t.get('symbol') for t in tokens]}")

        return {"tokens": tokens}
    except Exception as e:
        logger.error(f"Error in extract_tokens_node: {e}")
        return {"tokens": [], "error": str(e)}


async def search_token_info_node(state: GraphState) -> dict:
    """Node 3: Search market data for extracted tokens.

    Calls external APIs (CMC/GeckoTerminal) to get price and market data.
    """
    logger.info(f"Node: search_token_info for news {state['news_id']}")

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
                logger.warning(f"Failed to get info for {symbol}: {e}")
                # Continue with other tokens

        logger.info(f"Retrieved market data for {len(token_details)} tokens")
        return {"token_details": token_details}
    except ImportError:
        logger.warning("CMC client not available, skipping token info search")
        return {"token_details": {}}
    except Exception as e:
        logger.error(f"Error in search_token_info_node: {e}")
        return {"token_details": {}, "error": str(e)}


async def rag_knowledge_node(state: GraphState) -> dict:
    """Node 3.5: Retrieve relevant knowledge from RAG knowledge base.

    Enhances analysis with Web3 domain knowledge from the knowledge base.
    """
    logger.info(f"Node: rag_knowledge for news {state['news_id']}")

    tokens = state.get("tokens") or []
    title = state.get("title", "")
    content = state.get("content", "")

    # Build search query from news content
    query = f"{title}. {content[:500]}"  # First 500 chars for context

    # Extract token symbols for filtering
    token_symbols = []
    if tokens:
        token_symbols = [
            t.get("symbol") if isinstance(t, dict) else t.symbol
            for t in tokens
        ]

    try:
        from app.rag.chain import get_rag_chain

        rag = get_rag_chain(top_k=3, threshold=0.6)

        # Query with token filter if available
        result = await rag.query(
            query,
            filter_tokens=token_symbols if token_symbols else None,
        )

        rag_context = result.get("answer", "")
        sources = result.get("sources", [])

        logger.info(f"RAG retrieved {len(sources)} chunks, context length: {len(rag_context)}")

        return {
            "rag_context": rag_context,
            "rag_sources": sources,
        }

    except ImportError:
        logger.warning("RAG chain not available")
        return {"rag_context": None, "rag_sources": []}
    except Exception as e:
        logger.error(f"Error in rag_knowledge_node: {e}")
        return {"rag_context": None, "rag_sources": [], "error": str(e)}


async def kg_knowledge_node(state: GraphState) -> dict:
    """Node 3.6: Retrieve entity relationships from Knowledge Graph.

    Enhances analysis with entity relationship data from Neo4j.
    """
    logger.info(f"Node: kg_knowledge for news {state['news_id']}")

    tokens = state.get("tokens") or []
    title = state.get("title", "")
    content = state.get("content", "")

    try:
        from app.kg.client import Neo4jClient, Neo4jSettings
        from app.kg.query import GraphQuery

        # Create Neo4j client
        settings = Neo4jSettings()
        client = await Neo4jClient.create(settings)

        try:
            query_service = GraphQuery(client)

            # Search for projects mentioned in news
            kg_context_parts = []

            # Extract project names from title/content (simple heuristic)
            # In production, use NER or LLM extraction
            project_keywords = set()

            # Add token symbols as potential projects
            for token in tokens:
                symbol = token.get("symbol") if isinstance(token, dict) else token.symbol
                project_keywords.add(symbol)

            # Search projects by keywords from title
            words = set(title.lower().split() + content.lower()[:200].split())
            for word in words:
                if len(word) > 3:  # Filter short words
                    project_keywords.add(word.capitalize())

            # Query knowledge graph for each potential project
            kg_entities = {"projects": [], "tokens": [], "relationships": []}

            for keyword in list(project_keywords)[:5]:  # Limit to 5 searches
                # Search for projects
                projects = await query_service.search_projects_by_keyword(keyword, limit=3)
                for project in projects:
                    if project not in kg_entities["projects"]:
                        kg_entities["projects"].append(project)

                        # Get related entities
                        context = await query_service.get_project_context(project.get("name", ""))
                        if context:
                            kg_entities["tokens"].extend(context.get("tokens", []))
                            kg_entities["relationships"].extend(context.get("team", []))
                            kg_entities["relationships"].extend(context.get("investors", []))

            # Format KG context for LLM
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
            logger.info(f"KG retrieved {len(kg_entities['projects'])} projects, context length: {len(kg_context)}")

            return {
                "kg_context": kg_context,
                "kg_entities": kg_entities,
            }

        finally:
            await client.close()

    except ImportError:
        logger.warning("Knowledge graph module not available")
        return {"kg_context": None, "kg_entities": {}}
    except Exception as e:
        logger.error(f"Error in kg_knowledge_node: {e}")
        return {"kg_context": None, "kg_entities": {}, "error": str(e)}


async def trend_analysis_node(state: GraphState) -> dict:
    """Node 4: Analyze price trend based on news and token data.

    Combines news content with market data, RAG knowledge, and KG relationships to predict trend.
    """
    logger.info(f"Node: trend_analysis for news {state['news_id']}")

    llm = get_llm()

    # Format token data for prompt
    token_details = state.get("token_details") or {}
    token_data_str = "\n".join(
        f"- {symbol}: ${data.get('price', 'N/A')} "
        f"(24h: {data.get('change_24h', 'N/A')}%, "
        f"MCap: ${data.get('market_cap', 'N/A')})"
        for symbol, data in token_details.items()
    )
    if not token_data_str:
        token_data_str = "No token market data available"

    # Get RAG context if available
    rag_context = state.get("rag_context")
    if rag_context:
        logger.info(f"Using RAG context (length: {len(rag_context)})")

    # Get KG context if available
    kg_context = state.get("kg_context")
    if kg_context:
        logger.info(f"Using KG context (length: {len(kg_context)})")

    # Combine RAG and KG context
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
        logger.error(f"Error in trend_analysis_node: {e}")
        return {"trend_analysis": "", "error": str(e)}


async def generate_recommendation_node(state: GraphState) -> dict:
    """Node 5: Generate final trading recommendation.

    Produces buy/sell/hold recommendation with risk level.
    """
    logger.info(f"Node: generate_recommendation for news {state['news_id']}")

    llm = get_llm()

    # JSON schema for DeepSeek
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["buy", "sell", "hold"]},
            "reasoning": {"type": "string"},
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["action", "reasoning", "risk_level"],
    }

    # Use neutral prompt if we skipped analysis
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
            logger.error(f"Error in generate_recommendation_node: {e}")
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
            logger.error(f"Error in generate_recommendation_node: {e}")
            return {
                "recommendation": "hold",
                "risk_level": "low",
                "recommendation_reasoning": f"Analysis error: {str(e)}",
            }


def should_continue_route(state: GraphState) -> str:
    """Routing function: decide whether to continue with full analysis.

    Returns:
        "continue": Proceed with token extraction and full analysis
        "skip": Jump to final recommendation (for neutral news)
    """
    if state.get("should_continue", True):
        return "continue"
    return "skip"
