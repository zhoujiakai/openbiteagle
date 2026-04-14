#!/usr/bin/env python
"""新闻分析图谱调试脚本。

可视化图谱结构并提供手动测试功能。
"""

import asyncio
import os
from pathlib import Path

# 将项目根目录添加到路径
project_root = Path(__file__).parent.parent
import sys

sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv(project_root / ".env")


def visualize_graph():
    """打印图谱的 ASCII 可视化。"""
    from tasks.task2_analyze_flow.graph import build_news_analysis_graph

    print("=" * 60)
    print("新闻分析图谱结构")
    print("=" * 60)

    graph = build_news_analysis_graph()
    graph.get_graph().print_ascii()

    print("\n" + "=" * 60)
    print("图谱节点:")
    print("=" * 60)

    graph_dict = graph.get_graph()
    # 节点可能是字符串或带有 id 属性的对象
    for node in graph_dict.nodes:
        node_id = node if isinstance(node, str) else getattr(node, "id", str(node))
        print(f"  - {node_id}")

    print("\n" + "=" * 60)
    print("入口点:", graph_dict.entry_point)
    print("=" * 60)


async def test_manual_analysis():
    """手动测试分析流程。

    需要在 .env 中设置 OPENAI_API_KEY
    """
    from tasks.task2_analyze_flow import build_news_analysis_graph

    # 检查 API 密钥
    if not os.getenv("OPENAI_API_KEY"):
        print("错误: 未在 .env 中设置 OPENAI_API_KEY")
        return

    print("\n" + "=" * 60)
    print("手动测试: 正在运行分析")
    print("=" * 60)

    graph = build_news_analysis_graph()

    # 测试新闻条目
    test_input = {
        "news_id": 999,
        "title": "Ethereum ETF Approved by SEC",
        "content": "The SEC has officially approved spot Ethereum ETFs, "
        "opening the door for mainstream institutional investment. "
        "Major firms including BlackRock and Fidelity will launch trading next week.",
    }

    print(f"\n正在分析: {test_input['title']}")
    print(f"内容: {test_input['content'][:100]}...")

    try:
        result = await graph.ainvoke(test_input)

        print("\n" + "-" * 60)
        print("分析结果:")
        print("-" * 60)
        print(f"  投资价值: {result.get('investment_value')}")
        print(f"  置信度: {result.get('investment_confidence')}")
        print(f"  代币: {[t['symbol'] for t in (result.get('tokens') or [])]}")
        print(f"  建议: {result.get('recommendation')}")
        print(f"  风险等级: {result.get('risk_level')}")
        print(f"  理由: {result.get('recommendation_reasoning')}")

    except Exception as e:
        print(f"\n分析过程中出错: {e}")
        import traceback

        traceback.print_exc()


def main():
    """主入口。"""
    import argparse

    parser = argparse.ArgumentParser(description="调试新闻分析图谱")
    parser.add_argument(
        "action", choices=["visualize", "test"], help="要执行的操作"
    )
    args = parser.parse_args()

    if args.action == "visualize":
        visualize_graph()
    elif args.action == "test":
        asyncio.run(test_manual_analysis())


if __name__ == "__main__":
    main()
