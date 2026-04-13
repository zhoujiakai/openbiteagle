#!/usr/bin/env python
"""测试 LangSmith 追踪新闻分析图。

此脚本在启用 LangSmith 追踪的情况下运行新闻分析，
以便在 LangSmith UI 中查看执行追踪。"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import cfg
from tasks.task2_analyze_flow import build_news_analysis_graph


def print_header(text: str):
    """打印章节标题。"""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


async def test_langsmith_tracing():
    """测试带有 LangSmith 追踪的新闻分析图。"""
    print_header("LangSmith 追踪测试")

    # 检查 LangSmith 配置
    print("\n[LangSmith 配置]")
    print("-" * 70)
    print(f"LANGCHAIN_TRACING_V2: {cfg.langsmith.LANGCHAIN_TRACING_V2}")
    print(f"LANGCHAIN_PROJECT: {cfg.langsmith.LANGCHAIN_PROJECT}")
    print(f"LANGCHAIN_API_KEY: {'***' + cfg.langsmith.LANGCHAIN_API_KEY[-4:] if cfg.langsmith.LANGCHAIN_API_KEY else '未设置'}")

    if cfg.langsmith.LANGCHAIN_TRACING_V2.lower() != "true":
        print("\n⚠️  警告: LANGCHAIN_TRACING_V2 未设置为 'true'")
        print("   追踪将不会启用。")
        print("\n   要启用 LangSmith 追踪，请在 .env 中添加:")
        print("   LANGCHAIN_TRACING_V2=true")
        print("   LANGCHAIN_API_KEY=你的-langsmith-api-key")
        return

    if not cfg.langsmith.LANGCHAIN_API_KEY:
        print("\n⚠️  警告: LANGCHAIN_API_KEY 未设置")
        print("   追踪可能无法正常工作。")
        print("\n   在以下地址获取 API Key: https://smith.langchain.com/")
        return

    print("\n✓ LangSmith 追踪已配置")

    # 构建图
    print("\n[构建分析图]")
    print("-" * 70)
    graph = build_news_analysis_graph()
    print("✓ 分析图构建成功")

    # 测试输入
    test_input = {
        "news_id": 999,
        "title": "比特币 ETF 获批推动加密市场飙升",
        "content": "SEC 已批准首批比特币现货 ETF，标志着加密货币采用的分水岭时刻。包括贝莱德和富达在内的大型金融机构将立即开始交易。分析师预测这可能带来数十亿美元的机构投资。",
    }

    print("\n[测试输入]")
    print("-" * 70)
    print(f"标题: {test_input['title']}")
    print(f"内容: {test_input['content'][:80]}...")

    # 启用追踪运行分析
    print("\n[启用追踪运行分析]")
    print("-" * 70)
    print("在 LangSmith UI 中查看实时追踪:")
    print(f"🔗 https://smith.langchain.com/o/{cfg.langsmith.LANGCHAIN_PROJECT if cfg.langsmith.LANGCHAIN_PROJECT else 'default'}/projects?tab=traces")
    print()

    try:
        result = await graph.ainvoke(test_input)

        print("\n[分析结果]")
        print("-" * 70)
        print(f"投资价值: {result.get('investment_value')}")
        print(f"置信度: {result.get('investment_confidence')}")
        print(f"推荐: {result.get('recommendation')}")
        print(f"风险等级: {result.get('risk_level')}")

        print("\n✓ 分析完成 - 请在 LangSmith UI 中查看详细追踪")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    print_header("LangSmith 追踪测试完成")


def main():
    """主入口。"""
    asyncio.run(test_langsmith_tracing())


if __name__ == "__main__":
    main()
