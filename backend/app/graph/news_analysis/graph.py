"""LangGraph construction for news analysis workflow.

This module builds the StateGraph that defines the analysis pipeline.
"""

import logging

from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.graph.news_analysis.nodes import (
    extract_tokens_node,
    generate_recommendation_node,
    investment_value_node,
    kg_knowledge_node,
    rag_knowledge_node,
    search_token_info_node,
    should_continue_route,
    trend_analysis_node,
)
from app.graph.news_analysis.state import GraphState

logger = logging.getLogger(__name__)


def get_tracing_config(metadata: dict | None = None) -> dict:
    """Get tracing configuration for LangSmith.

    Args:
        metadata: Optional additional metadata to include in traces

    Returns:
        Configuration dict for LangGraph invoke
    """
    config = {}

    if settings.LANGCHAIN_TRACING_V2.lower() == "true":
        # Add metadata for LangSmith tracing
        trace_metadata = {
            "project": settings.LANGCHAIN_PROJECT,
            "graph_name": "news_analysis",
        }
        if metadata:
            trace_metadata.update(metadata)

        config["metadata"] = trace_metadata
        logger.info(f"LangSmith tracing enabled for project: {settings.LANGCHAIN_PROJECT}")

    return config


def build_news_analysis_graph():
    """Build the news analysis LangGraph.

    The graph has the following structure:

    ┌─────────────────────┐
    │ investment_value    │  Node 1: Judge investment value
    └──────────┬──────────┘
               │
         ┌─────┴─────┐
         │  Router   │  (should_continue?)
         └─────┬─────┘
        continue│       │skip
    ┌───────────┘       └──────────────────────┐
    │                                         │
    ▼                                         ▼
┌──────────────┐                    ┌──────────────────┐
│extract_tokens│  Node 2            │generate_recommend│
└──────┬───────┘                    └────────┬─────────┘
       │                                     │
       ▼                                     │
┌────────────────┐                          │
│search_token_info│ Node 3                  │
└───────┬────────┘                          │
        │                                   │
        ▼                                   │
┌────────────────┐                          │
│ rag_knowledge  │  Node 3.5 (RAG retrieval)│
└───────┬────────┘                          │
        │                                   │
        ▼                                   │
┌────────────────┐                          │
│  kg_knowledge  │  Node 3.6 (KG retrieval) │
└───────┬────────┘                          │
        │                                   │
        ▼                                   │
┌──────────────┐                            │
│trend_analysis│ Node 4 (enhanced with RAG+KG)│
└──────┬───────┘                            │
       │                                    │
       └────────────┬───────────────────────┘
                    ▼
            ┌───────────────┐
            │  recommendation│ Node 5
            └───────┬───────┘
                    │
                    ▼
                   END
    """
    # Create the state graph
    graph = StateGraph(GraphState)

    # Add all nodes
    graph.add_node("investment_value", investment_value_node)
    graph.add_node("extract_tokens", extract_tokens_node)
    graph.add_node("search_token_info", search_token_info_node)
    graph.add_node("rag_knowledge", rag_knowledge_node)
    graph.add_node("kg_knowledge", kg_knowledge_node)
    graph.add_node("trend_analysis", trend_analysis_node)
    graph.add_node("generate_recommendation", generate_recommendation_node)

    # Set entry point
    graph.set_entry_point("investment_value")

    # Add conditional routing after investment value check
    graph.add_conditional_edges(
        "investment_value",
        should_continue_route,
        {
            "continue": "extract_tokens",  # Proceed with full analysis
            "skip": "generate_recommendation",  # Skip to final recommendation
        },
    )

    # Add edges for the main analysis pipeline
    graph.add_edge("extract_tokens", "search_token_info")
    graph.add_edge("search_token_info", "rag_knowledge")
    graph.add_edge("rag_knowledge", "kg_knowledge")  # KG after RAG
    graph.add_edge("kg_knowledge", "trend_analysis")  # Trend after KG
    graph.add_edge("trend_analysis", "generate_recommendation")

    # End after recommendation
    graph.add_edge("generate_recommendation", END)

    # Compile the graph
    return graph.compile()


def visualize_graph():
    """Print an ASCII representation of the graph for debugging.

    This is useful for understanding the graph structure during development.
    """
    graph = build_news_analysis_graph()
    print(graph.get_graph().print_ascii())
    return graph
