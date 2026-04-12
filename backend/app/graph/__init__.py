"""Graph module for business analysis workflows.

This module provides LangGraph-based analysis pipelines for different
business scenarios. Each graph is a self-contained workflow that processes
inputs through multiple nodes and produces structured outputs.
"""

from app.graph.news_analysis import build_news_analysis_graph

# Graph registry - add new graphs here as they are implemented
GRAPHS = {
    "news_analysis": build_news_analysis_graph,
}


def get_graph(name: str):
    """Get a graph by name.

    Args:
        name: Graph name (e.g., "news_analysis")

    Returns:
        Compiled LangGraph instance

    Raises:
        ValueError: If graph name is not found
    """
    if name not in GRAPHS:
        available = list(GRAPHS.keys())
        raise ValueError(f"Unknown graph: {name!r}. Available: {available}")
    return GRAPHS[name]()


__all__ = ["get_graph", "GRAPHS"]
