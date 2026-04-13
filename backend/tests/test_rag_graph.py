#!/usr/bin/env python
"""测试带有 RAG 集成的完整 LangGraph。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tasks.task2_analyze_flow.graph import build_news_analysis_graph


# 测试新闻数据
TEST_NEWS = [
    {
        "id": 1,
        "title": "Arbitrum 推出新的 Stylus 升级，支持多种编程语言",
        "content": "Arbitrum 今日宣布推出 Stylus 升级，允许开发者使用 C++、Rust 和其他编程语言编写智能合约。这一升级将大幅降低开发门槛，预计将带来更多开发者进入 Arbitrum 生态系统。ARB 代币在消息传出后上涨 5%。",
    },
    {
        "id": 2,
        "title": "比特币 ETF 资金净流出，市场情绪转冷",
        "content": "昨日比特币 ETF 资金净流出约 2 亿美元，显示出机构投资者获利了结的迹象。分析师指出，这可能是短期调整信号，但长期趋势仍然看涨。",
    },
    {
        "id": 3,
        "title": "EigenLayer 开放再质押上限，TVL 突破 150 亿美元",
        "content": "以太坊再质押协议 EigenLayer 宣布开放再质押上限，总锁定价值 (TVL) 迅速突破 150 亿美元。EIGEN 代币即将上线交易，市场关注度极高。",
    },
]


async def main():
    """运行带有 RAG 的完整 LangGraph 分析。"""
    graph = build_news_analysis_graph()

    print("=" * 70)
    print("LangGraph + RAG 集成测试")
    print("=" * 70)
    print()

    for news in TEST_NEWS:
        print(f"\n{'='*70}")
        print(f"新闻 #{news['id']}: {news['title']}")
        print('='*70)
        print(f"内容: {news['content'][:100]}...")
        print()

        # 初始状态
        state = {
            "news_id": news["id"],
            "title": news["title"],
            "content": news["content"],
        }

        try:
            # 运行分析图
            result = await graph.ainvoke(state)

            # 打印结果
            print(f"\n📊 分析结果:")
            print(f"  投资价值: {result.get('investment_value', 'N/A')}")
            print(f"  置信度: {result.get('investment_confidence', 0):.2f}")

            tokens = result.get('tokens', [])
            if tokens:
                symbols = [t.get('symbol') if isinstance(t, dict) else t.symbol for t in tokens]
                print(f"  发现代币: {', '.join(symbols)}")

            # RAG 结果
            rag_sources = result.get('rag_sources', [])
            if rag_sources:
                print(f"  📚 RAG 来源: 检索到 {len(rag_sources)} 个分块")
                for i, source in enumerate(rag_sources[:2], 1):
                    print(f"    [{i}] {source.get('content', '')[:60]}...")

            print(f"\n  📈 趋势分析: {result.get('trend_analysis', 'N/A')[:100]}...")

            print(f"\n  💡 推荐: {result.get('recommendation', 'N/A').upper()}")
            print(f"  风险等级: {result.get('risk_level', 'N/A')}")
            print(f"  推理: {result.get('recommendation_reasoning', 'N/A')[:100]}...")

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()

        print()


if __name__ == "__main__":
    asyncio.run(main())
