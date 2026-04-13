"""News analysis graph using LangGraph.

This module implements a multi-stage analysis pipeline for Web3 news items,
evaluating investment value, extracting tokens, searching market data,
analyzing trends, and generating trading recommendations.
"""

from tasks.task2_analyze_flow.graph import build_news_analysis_graph
from tasks.task2_analyze_flow.models import (
    RecommendationOutput,
    TokenExtractionOutput,
    TokenInfo,
)
from tasks.task2_analyze_flow.state import GraphState

__all__ = [
    "build_news_analysis_graph",
    "GraphState",
    "RecommendationOutput",
    "TokenExtractionOutput",
    "TokenInfo",
]
