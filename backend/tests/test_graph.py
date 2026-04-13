#!/usr/bin/env python
"""Test script for news analysis graph.

Runs a real news item through the graph and prints the execution process.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tasks.task2_analyze_flow import build_news_analysis_graph


def print_header(text: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


def print_section(title: str, content: str):
    """Print a section with title and content."""
    print(f"\n[{title}]")
    print("-" * 70)
    print(content)


async def test_graph():
    """Test the news analysis graph with real data."""
    print_header("LangGraph News Analysis Test")

    # Sample news items for testing
    test_cases = [
        {
            "name": "Bullish News (ETF Approval)",
            "input": {
                "news_id": 1,
                "title": "Ethereum ETF Approved by SEC",
                "content": "The SEC has officially approved spot Ethereum ETFs, opening the door for mainstream institutional investment. Major firms including BlackRock and Fidelity will launch trading next week. Analysts predict significant inflows into Ethereum.",
            },
        },
        {
            "name": "Bearish News (Regulatory Crackdown)",
            "input": {
                "news_id": 2,
                "title": "Binance Faces $4B Fine from DOJ",
                "content": "The Department of Justice has imposed a record $4 billion penalty on Binance for sanctions violations. The exchange has agreed to compliance monitoring and may face further restrictions on US operations.",
            },
        },
        {
            "name": "Neutral News (General Info)",
            "input": {
                "news_id": 3,
                "title": "Crypto Industry Overview",
                "content": "Cryptocurrency has evolved significantly over the past decade. Bitcoin remains the largest by market cap, followed by Ethereum. Many new projects emerge each year in various sectors including DeFi, NFTs, and gaming.",
            },
        },
    ]

    # Build graph
    print("\nBuilding graph...")
    graph = build_news_analysis_graph()
    print("Graph built successfully!")

    # Run test for each case
    for i, test_case in enumerate(test_cases, 1):
        print_header(f"Test Case {i}/{len(test_cases)}: {test_case['name']}")

        # Print input
        print_section("Input", f"Title: {test_case['input']['title']}\nContent: {test_case['input']['content'][:100]}...")

        # Run analysis
        print("\n[Running Analysis...]")
        try:
            result = await graph.ainvoke(test_case["input"])

            # Print results
            print_section("Investment Value",
                f"Value: {result.get('investment_value', 'N/A')}\n"
                f"Confidence: {result.get('investment_confidence', 'N/A')}\n"
                f"Reasoning: {result.get('investment_reasoning', 'N/A')}"
            )

            tokens = result.get('tokens') or []
            if tokens:
                token_list = ", ".join([f"{t['symbol']} ({t.get('name', 'N/A')})" for t in tokens])
                print_section("Extracted Tokens", token_list)
            else:
                print_section("Extracted Tokens", "None (skipped due to neutral value)")

            token_details = result.get('token_details') or {}
            if token_details:
                detail_lines = []
                for symbol, data in token_details.items():
                    detail_lines.append(f"{symbol}: ${data.get('price', 'N/A')} ({data.get('change_24h', 'N/A')}% 24h)")
                print_section("Token Market Data", "\n".join(detail_lines))
            else:
                print_section("Token Market Data", "Not available")

            print_section("Trend Analysis", result.get('trend_analysis', 'N/A'))

            print_section("Recommendation",
                f"Action: {result.get('recommendation', 'N/A')}\n"
                f"Risk Level: {result.get('risk_level', 'N/A')}\n"
                f"Reasoning: {result.get('recommendation_reasoning', 'N/A')}"
            )

            # Check for errors
            if result.get('error'):
                print_section("Warning", f"Error occurred: {result['error']}")

            print("\n✓ Test case completed")

        except Exception as e:
            print_section("Error", str(e))
            import traceback
            traceback.print_exc()

    print_header("All Tests Completed")


def main():
    """Main entry point."""
    asyncio.run(test_graph())


if __name__ == "__main__":
    main()
