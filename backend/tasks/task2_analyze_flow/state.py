"""新闻分析工作流的 GraphState 定义。

状态在节点之间传递，并在整个分析流水线中累积信息。
"""

from typing import Optional

from typing_extensions import TypedDict


class GraphState(TypedDict):
    """新闻分析图的状态。

    随着工作流在各节点中推进，此状态会被不断更新。
    """

    # 输入字段（必填）
    news_id: int
    title: str
    content: str

    # 节点 1：投资价值判断
    investment_value: Optional[str]  # "bullish" | "bearish" | "neutral"
    investment_confidence: Optional[float]  # 0.0 - 1.0
    investment_reasoning: Optional[str]

    # 节点 2：代币提取
    tokens: Optional[list[dict]]  # TokenInfo 字典列表

    # 节点 3：代币市场数据
    token_details: Optional[dict[str, dict]]  # {symbol: {price, market_cap, change_24h}}

    # 节点 3.5：RAG 知识检索
    rag_context: Optional[str]  # 检索到的知识库上下文
    rag_sources: Optional[list[dict]]  # 来源分块，用于参考

    # 节点 3.6：KG 知识检索
    kg_context: Optional[str]  # 检索到的知识图谱上下文
    kg_entities: Optional[dict]  # 图谱中的相关实体

    # 节点 4：趋势分析（增强 RAG+KG）
    trend_analysis: Optional[str]

    # 节点 5：交易建议
    recommendation: Optional[str]  # "buy" | "sell" | "hold"
    risk_level: Optional[str]  # "low" | "medium" | "high"
    recommendation_reasoning: Optional[str]

    # 流程控制
    should_continue: bool  # 若为 False，跳过直接生成最终建议
    error: Optional[str]  # 出错时的错误信息
