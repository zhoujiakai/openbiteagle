"""演示 node 怎么用"""

import asyncio

from data import create_logger

logger = create_logger("分析流水线::演示")

from tasks.task2_analyze_flow.nodes import (
    extract_tokens_node,
    generate_recommendation_node,
    investment_value_node,
    search_token_info_node,
    trend_analysis_node,
)


async def main():
    state = {
        "news_id": 1,
        "title": "Bitcoin ETF approved by SEC",
        "content": "The SEC has officially approved the Bitcoin ETF application.",
    }

    # Node 1: 投资价值判断
    result1 = await investment_value_node(state)
    state.update(result1)
    print("investment_value:", result1)

    # Node 2: 提取代币
    result2 = await extract_tokens_node(state)
    state.update(result2)
    print("extract_tokens:", result2)

    # Node 3: 查询代币行情
    result3 = await search_token_info_node(state)
    state.update(result3)
    print("token_info:", result3)

    # Node 4: 趋势分析
    result4 = await trend_analysis_node(state)
    state.update(result4)
    print("trend_analysis:", result4)

    # Node 5: 生成交易建议
    result5 = await generate_recommendation_node(state)
    state.update(result5)
    print("recommendation:", result5)


async def run_graph():
    """演示整个 graph 流水线一键跑"""
    from tasks.task2_analyze_flow.graph import build_news_analysis_graph

    graph = build_news_analysis_graph()
    result = await graph.ainvoke({
        "news_id": 2,
        "title": "Bitcoin ETF approved by SEC",
        "content": "The SEC has officially approved the Bitcoin ETF application.",
    })
    for k, v in result.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    asyncio.run(run_graph())
