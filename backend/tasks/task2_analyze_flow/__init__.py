"""使用 LangGraph 的新闻分析图。

本模块实现了 Web3 新闻条目的多阶段分析流水线，
包括评估投资价值、提取代币、搜索市场数据、
分析趋势并生成交易建议。
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
