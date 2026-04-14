"""业务分析工作流的图模块。

该模块提供基于 LangGraph 的分析流水线，用于不同的业务场景。
每个图是一个独立的工作流，通过多个节点处理输入并生成结构化输出。
"""

from tasks.task2_analyze_flow import build_news_analysis_graph

# Graph 注册表 - 新的 graph 实现后在此添加
GRAPHS = {
    "news_analysis": build_news_analysis_graph,
}


def get_graph(name: str):
    """根据名称获取图。

    Args:
        name: 图名称（例如 "news_analysis"）

    Returns:
        已编译的 LangGraph 实例

    Raises:
        ValueError: 如果图名称未找到
    """
    if name not in GRAPHS:
        available = list(GRAPHS.keys())
        raise ValueError(f"Unknown graph: {name!r}. Available: {available}")
    return GRAPHS[name]()


__all__ = ["get_graph", "GRAPHS"]
