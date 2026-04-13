"""新闻分析节点的中文提示词模板。

每个提示词旨在引导 LLM 生成特定的结构化输出。
"""

# 投资价值判断提示词
INVESTMENT_VALUE_PROMPT = """你是一名 Web3 投资分析师。请分析以下新闻并判断其投资价值。

## 新闻内容
标题：{title}
正文：{content}

## 分析维度

1. **代币/项目明确性**：该新闻是否提到了具体的加密货币或项目？

2. **市场影响**：是否存在可能影响价格的实质性利好或利空信息？

3. **信息质量**：信息来源是否可靠？信息是否可验证？

4. **市场关注度**：该新闻是否可能引发显著的市场关注或交易量变化？

## 任务

请对投资价值进行分类并说明理由：
- **bullish**（看涨）：利好信息，暗示价格上涨潜力
- **bearish**（看跌）：利空信息，暗示价格下跌风险
- **neutral**（中性）：无明显投资价值、信息泛泛或数据不足

请提供：
1. value (bullish/bearish/neutral)
2. confidence (0.0-1.0)
3. reasoning
"""

# 代币提取提示词
TOKEN_EXTRACTION_PROMPT = """你是一名加密货币专家。请从新闻中提取所有相关的加密货币代币。

## 新闻内容
标题：{title}
正文：{content}

## 任务

识别新闻中提到的、符合以下条件的加密货币：
- 在主流交易所活跃交易
- 具有合理的市值和流动性
- 与新闻内容直接相关

对于每个代币，请提供：
1. **symbol**：交易代码（如 BTC、ETH、SOL）
2. **name**：全称（如 Bitcoin、Ethereum、Solana）
3. **confidence**：该代币与新闻主题的相关程度（0.0-1.0）

排除以下情况：
- 已停止维护/废弃的项目
- 仅被一带而过、与主题无关的代币
- 未指向具体项目的泛泛引用

如果未找到相关代币，请返回空列表。
"""

# 趋势分析提示词（原始版本，不含 RAG）
TREND_ANALYSIS_PROMPT = """你是一名 Web3 市场分析师。请分析该新闻的趋势影响。

## 新闻内容
标题：{title}
正文：{content}

## 投资价值评估
分类：{investment_value}
置信度：{confidence}

## 代币市场数据
{token_data}

## 任务

分析潜在的价格趋势影响：
1. **短期方向**：预期的即时市场反应
2. **关键因素**：具体哪些因素将驱动价格变动
3. **风险考量**：哪些因素可能逆转这一趋势
4. **时间范围**：影响可能持续多长时间

请提供简洁的趋势分析（2-3 句话）。
"""

# 趋势分析提示词（带 RAG 增强）
TREND_ANALYSIS_WITH_RAG_PROMPT = """你是一名拥有知识库访问权限的 Web3 市场分析师。请结合知识库信息分析该新闻的趋势影响。

## 新闻内容
标题：{title}
正文：{content}

## 投资价值评估
分类：{investment_value}
置信度：{confidence}

## 代币市场数据
{token_data}

## 知识库上下文
{rag_context}

## 任务

结合新闻和知识库信息分析潜在的价格趋势影响：
1. **短期方向**：预期的即时市场反应
2. **关键因素**：具体哪些因素将驱动价格变动（结合知识库洞察）
3. **风险考量**：哪些因素可能逆转这一趋势（结合知识库中的项目基本面）
4. **时间范围**：影响可能持续多长时间

请提供简洁的趋势分析（2-3 句话），充分利用知识库获得更深入的洞察。
"""

# 交易建议提示词
RECOMMENDATION_PROMPT = """你是一名稳健型交易顾问。请根据分析结果生成交易建议。

## 分析摘要

**新闻**：{title}

**投资价值**：{investment_value}（置信度：{confidence}）

**趋势分析**：{trend_analysis}

## 任务

生成交易建议：
- **buy**（买入）：信号强劲且风险可控
- **sell**（卖出）：利空信号强劲且风险可控
- **hold**（持有）：前景不明、信号中性或风险过高

同时评估风险等级：
- **low**（低风险）：成熟代币、明确催化剂、不确定性低
- **medium**（中风险）：较新代币或不确定性中等
- **high**（高风险）：高度投机、流动性低或不确定性极高

请提供：
1. action (buy/sell/hold)
2. risk_level (low/medium/high)
3. reasoning
"""

# 中性兜底提示词（无投资价值时使用）
NEUTRAL_RECOMMENDATION_PROMPT = """你是一名稳健型交易顾问。

该新闻经过分析后被判定为无显著投资价值（中性）。

## 新闻内容
标题：{title}
正文：{content}

## 任务

由于该新闻没有明确的投资价值或可操作的信号，请建议 action=hold，risk_level=low。

请提供：
1. action (hold)
2. risk_level (low)
3. reasoning
"""


def format_investment_value_prompt(title: str, content: str) -> str:
    """格式化投资价值判断提示词。"""
    return INVESTMENT_VALUE_PROMPT.format(title=title, content=content or "")


def format_token_extraction_prompt(title: str, content: str) -> str:
    """格式化代币提取提示词。"""
    return TOKEN_EXTRACTION_PROMPT.format(title=title, content=content or "")


def format_trend_analysis_prompt(
    title: str,
    content: str,
    investment_value: str,
    confidence: float,
    token_data: str,
    rag_context: str | None = None,
) -> str:
    """格式化趋势分析提示词。"""
    if rag_context:
        return TREND_ANALYSIS_WITH_RAG_PROMPT.format(
            title=title,
            content=content or "",
            investment_value=investment_value,
            confidence=confidence,
            token_data=token_data or "无代币数据",
            rag_context=rag_context or "无额外上下文",
        )
    return TREND_ANALYSIS_PROMPT.format(
        title=title,
        content=content or "",
        investment_value=investment_value,
        confidence=confidence,
        token_data=token_data or "无代币数据",
    )


def format_recommendation_prompt(
    title: str,
    investment_value: str,
    confidence: float,
    trend_analysis: str,
) -> str:
    """格式化交易建议提示词。"""
    return RECOMMENDATION_PROMPT.format(
        title=title,
        investment_value=investment_value,
        confidence=confidence,
        trend_analysis=trend_analysis or "无趋势分析",
    )


def format_neutral_recommendation_prompt(title: str, content: str) -> str:
    """格式化中性（跳过）建议提示词。"""
    return NEUTRAL_RECOMMENDATION_PROMPT.format(title=title, content=content or "")
