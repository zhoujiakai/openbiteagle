"""GraphState definition for news analysis workflow.

The state is passed between nodes and accumulates information
throughout the analysis pipeline.
"""

from typing import Optional

from typing_extensions import TypedDict


class GraphState(TypedDict):
    """State for the news analysis graph.

    This state is updated as the workflow progresses through each node.
    """

    # Input fields (required)
    news_id: int
    title: str
    content: str

    # Node 1: Investment value judgment
    investment_value: Optional[str]  # "bullish" | "bearish" | "neutral"
    investment_confidence: Optional[float]  # 0.0 - 1.0
    investment_reasoning: Optional[str]

    # Node 2: Token extraction
    tokens: Optional[list[dict]]  # List of TokenInfo as dict

    # Node 3: Token market data
    token_details: Optional[dict[str, dict]]  # {symbol: {price, market_cap, change_24h}}

    # Node 3.5: RAG knowledge retrieval
    rag_context: Optional[str]  # Retrieved knowledge base context
    rag_sources: Optional[list[dict]]  # Source chunks for reference

    # Node 3.6: KG knowledge retrieval
    kg_context: Optional[str]  # Retrieved knowledge graph context
    kg_entities: Optional[dict]  # Related entities from graph

    # Node 4: Trend analysis (enhanced with RAG+KG)
    trend_analysis: Optional[str]

    # Node 5: Recommendation
    recommendation: Optional[str]  # "buy" | "sell" | "hold"
    risk_level: Optional[str]  # "low" | "medium" | "high"
    recommendation_reasoning: Optional[str]

    # Flow control
    should_continue: bool  # If False, skip to final recommendation
    error: Optional[str]  # Error message if something failed
