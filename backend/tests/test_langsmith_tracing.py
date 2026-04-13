#!/usr/bin/env python
"""Test LangSmith tracing for news analysis graph.

This script runs a news analysis with LangSmith tracing enabled,
allowing you to view the execution trace in the LangSmith UI.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import cfg
from tasks.task2_analyze_flow import build_news_analysis_graph


def print_header(text: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


async def test_langsmith_tracing():
    """Test the news analysis graph with LangSmith tracing."""
    print_header("LangSmith Tracing Test")

    # Check LangSmith configuration
    print("\n[LangSmith Configuration]")
    print("-" * 70)
    print(f"LANGCHAIN_TRACING_V2: {cfg.langsmith.LANGCHAIN_TRACING_V2}")
    print(f"LANGCHAIN_PROJECT: {cfg.langsmith.LANGCHAIN_PROJECT}")
    print(f"LANGCHAIN_API_KEY: {'***' + cfg.langsmith.LANGCHAIN_API_KEY[-4:] if cfg.langsmith.LANGCHAIN_API_KEY else 'Not set'}")

    if cfg.langsmith.LANGCHAIN_TRACING_V2.lower() != "true":
        print("\n⚠️  Warning: LANGCHAIN_TRACING_V2 is not set to 'true'")
        print("   Tracing will not be enabled.")
        print("\n   To enable LangSmith tracing, add to your .env:")
        print("   LANGCHAIN_TRACING_V2=true")
        print("   LANGCHAIN_API_KEY=your-langsmith-api-key")
        return

    if not cfg.langsmith.LANGCHAIN_API_KEY:
        print("\n⚠️  Warning: LANGCHAIN_API_KEY is not set")
        print("   Tracing may not work properly.")
        print("\n   Get your API key at: https://smith.langchain.com/")
        return

    print("\n✓ LangSmith tracing is configured")

    # Build graph
    print("\n[Building Graph]")
    print("-" * 70)
    graph = build_news_analysis_graph()
    print("✓ Graph built successfully")

    # Test input
    test_input = {
        "news_id": 999,
        "title": "Bitcoin ETF Approval Sends Crypto Markets Surging",
        "content": "The SEC has approved the first spot Bitcoin ETFs, marking a watershed moment for cryptocurrency adoption. Major financial institutions including BlackRock and Fidelity will begin trading immediately. Analysts predict this could bring billions in institutional investment.",
    }

    print("\n[Test Input]")
    print("-" * 70)
    print(f"Title: {test_input['title']}")
    print(f"Content: {test_input['content'][:80]}...")

    # Run analysis with tracing
    print("\n[Running Analysis with Tracing]")
    print("-" * 70)
    print("Check LangSmith UI for live trace:")
    print(f"🔗 https://smith.langchain.com/o/{cfg.langsmith.LANGCHAIN_PROJECT if cfg.langsmith.LANGCHAIN_PROJECT else 'default'}/projects?tab=traces")
    print()

    try:
        result = await graph.ainvoke(test_input)

        print("\n[Analysis Results]")
        print("-" * 70)
        print(f"Investment Value: {result.get('investment_value')}")
        print(f"Confidence: {result.get('investment_confidence')}")
        print(f"Recommendation: {result.get('recommendation')}")
        print(f"Risk Level: {result.get('risk_level')}")

        print("\n✓ Analysis complete - Check LangSmith UI for detailed trace")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print_header("LangSmith Tracing Test Complete")


def main():
    """Main entry point."""
    asyncio.run(test_langsmith_tracing())


if __name__ == "__main__":
    main()
