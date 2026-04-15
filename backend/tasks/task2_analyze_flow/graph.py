"""新闻分析工作流的 LangGraph 构建。

本模块构建定义分析流水线的 StateGraph。
"""

from langgraph.graph import StateGraph, END

from app.core.config import cfg
from tasks.task2_analyze_flow.nodes import (
    extract_tokens_node,
    generate_recommendation_node,
    investment_value_node,
    kg_knowledge_node,
    rag_knowledge_node,
    search_token_info_node,
    should_continue_route,
    trend_analysis_node,
)
from tasks.task2_analyze_flow.state import GraphState
from app.data.logger import create_logger

logger = create_logger("分析流水线::graph")


def get_tracing_config(metadata: dict | None = None) -> dict:
    """获取 LangSmith 的追踪配置。

    Args:
        metadata: 可选的额外元数据，将包含在追踪记录中

    Returns:
        用于 LangGraph invoke 的配置字典
    """
    config = {}

    if cfg.langsmith.LANGCHAIN_TRACING_V2.lower() == "true":
        # 为 LangSmith 追踪添加元数据
        trace_metadata = {
            "project": cfg.langsmith.LANGCHAIN_PROJECT,
            "graph_name": "news_analysis",
        }
        if metadata:
            trace_metadata.update(metadata)

        config["metadata"] = trace_metadata
        logger.info(f"LangSmith tracing enabled for project: {cfg.langsmith.LANGCHAIN_PROJECT}")

    return config


def build_news_analysis_graph():
    """构建新闻分析 LangGraph。

    图的结构如下：

    ┌──────────────────┐
    │ investment_value │  Node 1: 投资价值判断
    └────────┬─────────┘
             │
       ┌─────┴───────┐
       │   Router    │  (should_continue?)
       └──┬────────┬─┘
     continue    skip
      │            └─┐
          ▼          │
  ┌──────────────┐   │
  │extract_tokens│   │ Node 2: 提取代币
  └──────┬───────┘   │
         ▼           │
  ┌─────────────────┐│
  │search_token_info││ Node 3: 查询行情
  └───────┬─────────┘│
          ▼          │
  ┌────────────────┐ │
  │ rag_knowledge  │ │ Node 3.5: RAG 检索
  └───────┬────────┘ │
          ▼          │
  ┌────────────────┐ │
  │  kg_knowledge  │ │ Node 3.6: KG 检索
  └───────┬────────┘ │
          ▼          │
  ┌──────────────┐   │
  │trend_analysis│   │ Node 4: 趋势分析
  └──────┬───────┘   │
         │           │
         ▼           ▼
  ┌────────────────────────┐
  │ generate_recommendation│  Node 5: 生成交易建议
  └──────────┬─────────────┘
             ▼
            END
    """
    # 创建状态图
    graph = StateGraph(GraphState)

    # 添加所有节点
    graph.add_node("investment_value", investment_value_node)
    graph.add_node("extract_tokens", extract_tokens_node)
    graph.add_node("search_token_info", search_token_info_node)
    graph.add_node("rag_knowledge", rag_knowledge_node)
    graph.add_node("kg_knowledge", kg_knowledge_node)
    graph.add_node("trend_analysis", trend_analysis_node)
    graph.add_node("generate_recommendation", generate_recommendation_node)

    # 设置入口点
    graph.set_entry_point("investment_value")

    # 在投资价值判断之后添加条件路由
    graph.add_conditional_edges(
        "investment_value",
        should_continue_route,
        {
            "continue": "extract_tokens",  # 继续完整分析
            "skip": "generate_recommendation",  # 跳过，直接生成建议
        },
    )

    # 添加主分析流水线的边
    graph.add_edge("extract_tokens", "search_token_info")
    graph.add_edge("search_token_info", "rag_knowledge")
    graph.add_edge("rag_knowledge", "kg_knowledge")  # RAG 之后执行 KG
    graph.add_edge("kg_knowledge", "trend_analysis")  # KG 之后执行趋势分析
    graph.add_edge("trend_analysis", "generate_recommendation")

    # 生成建议后结束
    graph.add_edge("generate_recommendation", END)

    # 编译图
    return graph.compile()


def visualize_graph():
    """打印图的 ASCII 表示，用于调试。

    在开发过程中有助于理解图的结构。
    """
    graph = build_news_analysis_graph()
    print(graph.get_graph().print_ascii())
    return graph

def main():
    visualize_graph()


if __name__ == "__main__":
    main()
