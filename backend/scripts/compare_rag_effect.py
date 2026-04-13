#!/usr/bin/env python
"""Compare analysis results with and without RAG."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tasks.task2_analyze_flow.graph import build_news_analysis_graph


# Test news - about a less known project that would benefit from RAG
TEST_NEWS = {
    "id": 1,
    "title": "Stabilizer Protocol 推出零滑点 DEX，解决 MEV 问题",
    "content": "Stabilizer Protocol 今日宣布推出创新的零滑点去中心化交易所，通过批量拍卖机制彻底解决 MEV 问题。协议采用独特的稳定币设计，允许用户在无滑点的情况下进行大额交易。这一创新可能改变 DEX 格局。",
}


async def run_with_rag(news: dict):
    """Run analysis WITH RAG enabled."""
    print("\n" + "="*70)
    print("🟢 WITH RAG (知识库增强)")
    print("="*70)

    graph = build_news_analysis_graph()
    state = {
        "news_id": news["id"],
        "title": news["title"],
        "content": news["content"],
    }

    result = await graph.ainvoke(state)

    # Extract key info
    tokens = result.get('tokens', [])
    symbols = [t.get('symbol') if isinstance(t, dict) else t.symbol for t in tokens]
    rag_sources = result.get('rag_sources', [])
    rag_context = result.get('rag_context', '')

    print(f"\n📊 Analysis:")
    print(f"  Investment: {result.get('investment_value')} ({result.get('investment_confidence'):.2f})")
    print(f"  Tokens: {', '.join(symbols) if symbols else 'None'}")
    print(f"  RAG Chunks: {len(rag_sources)} retrieved")

    if rag_context:
        preview = rag_context[:200].replace('\n', ' ')
        print(f"  RAG Context: {preview}...")

    print(f"\n📈 Trend Analysis:")
    trend = result.get('trend_analysis', '')
    print(f"  {trend[:300]}...")

    print(f"\n💡 Recommendation: {result.get('recommendation').upper()}")
    print(f"  Reasoning: {result.get('recommendation_reasoning', '')[:200]}...")

    return result


async def run_without_rag(news: dict):
    """Run analysis WITHOUT RAG (bypass RAG node)."""
    print("\n" + "="*70)
    print("🔴 WITHOUT RAG (仅 LLM)")
    print("="*70)

    # Temporarily disable RAG by mocking the node
    from tasks.task2_analyze_flow import nodes
    original_rag_node = nodes.rag_knowledge_node

    async def mock_rag_node(state):
        """Mock RAG node that returns no context."""
        return {
            "rag_context": None,
            "rag_sources": [],
        }

    nodes.rag_knowledge_node = mock_rag_node

    try:
        graph = build_news_analysis_graph()
        state = {
            "news_id": news["id"],
            "title": news["title"],
            "content": news["content"],
        }

        result = await graph.ainvoke(state)

        tokens = result.get('tokens', [])
        symbols = [t.get('symbol') if isinstance(t, dict) else t.symbol for t in tokens]

        print(f"\n📊 Analysis:")
        print(f"  Investment: {result.get('investment_value')} ({result.get('investment_confidence'):.2f})")
        print(f"  Tokens: {', '.join(symbols) if symbols else 'None'}")
        print(f"  RAG Chunks: 0 (disabled)")

        print(f"\n📈 Trend Analysis:")
        trend = result.get('trend_analysis', '')
        print(f"  {trend[:300]}...")

        print(f"\n💡 Recommendation: {result.get('recommendation').upper()}")
        print(f"  Reasoning: {result.get('recommendation_reasoning', '')[:200]}...")

        return result
    finally:
        nodes.rag_knowledge_node = original_rag_node


def compare_results(with_rag, without_rag):
    """Compare and highlight differences."""
    print("\n" + "="*70)
    print("📊 对比结果")
    print("="*70)

    # Investment comparison
    inv_with = with_rag.get('investment_value')
    inv_without = without_rag.get('investment_value')
    if inv_with != inv_without:
        print(f"\n🔄 投资判断变化:")
        print(f"  无 RAG: {inv_without}")
        print(f"  有 RAG: {inv_with}")
    else:
        print(f"\n✅ 投资判断一致: {inv_with}")

    # Confidence comparison
    conf_with = with_rag.get('investment_confidence', 0)
    conf_without = without_rag.get('investment_confidence', 0)
    diff = conf_with - conf_without
    if abs(diff) > 0.05:
        print(f"\n📈 置信度变化: {conf_without:.2f} → {conf_with:.2f} ({diff:+.2f})")

    # Trend analysis length (RAG should provide more context)
    trend_with = len(with_rag.get('trend_analysis', ''))
    trend_without = len(without_rag.get('trend_analysis', ''))
    print(f"\n📝 趋势分析长度:")
    print(f"  无 RAG: {trend_without} 字符")
    print(f"  有 RAG: {trend_with} 字符")

    # Recommendation comparison
    rec_with = with_rag.get('recommendation')
    rec_without = without_rag.get('recommendation')
    if rec_with != rec_without:
        print(f"\n🔄 推荐变化:")
        print(f"  无 RAG: {rec_without.upper()}")
        print(f"  有 RAG: {rec_with.upper()}")


async def main():
    """Run comparison test."""
    print("="*70)
    print("RAG 效果对比测试")
    print("="*70)
    print(f"\n测试新闻: {TEST_NEWS['title']}")
    print(f"内容: {TEST_NEWS['content'][:100]}...")

    # Run WITHOUT RAG first
    result_without = await run_without_rag(TEST_NEWS)

    # Run WITH RAG
    result_with = await run_with_rag(TEST_NEWS)

    # Compare
    compare_results(result_with, result_without)

    print("\n" + "="*70)
    print("✅ 对比测试完成")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
