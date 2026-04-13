#!/usr/bin/env python
"""Debug script for news analysis graph.

Visualizes graph structure and provides manual testing capabilities.
"""

import asyncio
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
import sys

sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment
load_dotenv(project_root / ".env")


def visualize_graph():
    """Print ASCII visualization of the graph."""
    from tasks.task2_analyze_flow.graph import build_news_analysis_graph

    print("=" * 60)
    print("News Analysis Graph Structure")
    print("=" * 60)

    graph = build_news_analysis_graph()
    graph.get_graph().print_ascii()

    print("\n" + "=" * 60)
    print("Graph Nodes:")
    print("=" * 60)

    graph_dict = graph.get_graph()
    # nodes may be strings or objects with id attribute
    for node in graph_dict.nodes:
        node_id = node if isinstance(node, str) else getattr(node, "id", str(node))
        print(f"  - {node_id}")

    print("\n" + "=" * 60)
    print("Entry Point:", graph_dict.entry_point)
    print("=" * 60)


async def test_manual_analysis():
    """Manually test the analysis pipeline.

    Requires OPENAI_API_KEY to be set in .env
    """
    from tasks.task2_analyze_flow import build_news_analysis_graph

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set in .env")
        return

    print("\n" + "=" * 60)
    print("Manual Test: Running Analysis")
    print("=" * 60)

    graph = build_news_analysis_graph()

    # Sample news item
    test_input = {
        "news_id": 999,
        "title": "Ethereum ETF Approved by SEC",
        "content": "The SEC has officially approved spot Ethereum ETFs, "
        "opening the door for mainstream institutional investment. "
        "Major firms including BlackRock and Fidelity will launch trading next week.",
    }

    print(f"\nAnalyzing: {test_input['title']}")
    print(f"Content: {test_input['content'][:100]}...")

    try:
        result = await graph.ainvoke(test_input)

        print("\n" + "-" * 60)
        print("Analysis Results:")
        print("-" * 60)
        print(f"  Investment Value: {result.get('investment_value')}")
        print(f"  Confidence: {result.get('investment_confidence')}")
        print(f"  Tokens: {[t['symbol'] for t in (result.get('tokens') or [])]}")
        print(f"  Recommendation: {result.get('recommendation')}")
        print(f"  Risk Level: {result.get('risk_level')}")
        print(f"  Reasoning: {result.get('recommendation_reasoning')}")

    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Debug news analysis graph")
    parser.add_argument(
        "action", choices=["visualize", "test"], help="Action to perform"
    )
    args = parser.parse_args()

    if args.action == "visualize":
        visualize_graph()
    elif args.action == "test":
        asyncio.run(test_manual_analysis())


if __name__ == "__main__":
    main()
