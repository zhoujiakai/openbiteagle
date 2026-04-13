#!/usr/bin/env python
"""新闻分析图测试脚本。

使用真实新闻数据运行分析图并打印执行过程。"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tasks.task2_analyze_flow import build_news_analysis_graph


def print_header(text: str):
    """打印章节标题。"""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


def print_section(title: str, content: str):
    """打印带标题的内容段落。"""
    print(f"\n[{title}]")
    print("-" * 70)
    print(content)


async def test_graph():
    """使用真实数据测试新闻分析图。"""
    print_header("LangGraph 新闻分析测试")

    # 测试用例
    test_cases = [
        {
            "name": "利好新闻（ETF 获批）",
            "input": {
                "news_id": 1,
                "title": "以太坊 ETF 获得 SEC 批准",
                "content": "SEC 已正式批准以太坊现货 ETF，为主流机构投资打开了大门。包括贝莱德和富达在内的大型公司将于下周开始交易。分析师预测以太坊将迎来大量资金流入。",
            },
        },
        {
            "name": "利空新闻（监管打击）",
            "input": {
                "news_id": 2,
                "title": "币安面临司法部 40 亿美元罚款",
                "content": "司法部因制裁违规对币安处以创纪录的 40 亿美元罚款。该交易所已同意接受合规监控，并可能面临对美国业务的进一步限制。",
            },
        },
        {
            "name": "中性新闻（一般信息）",
            "input": {
                "news_id": 3,
                "title": "加密行业概览",
                "content": "加密货币在过去十年中有了显著发展。比特币仍然是市值最大的加密货币，其次是以太坊。每年都有许多新项目在 DeFi、NFT 和游戏等各个领域涌现。",
            },
        },
    ]

    # 构建图
    print("\n正在构建分析图...")
    graph = build_news_analysis_graph()
    print("分析图构建成功！")

    # 运行每个测试用例
    for i, test_case in enumerate(test_cases, 1):
        print_header(f"测试用例 {i}/{len(test_cases)}: {test_case['name']}")

        # 打印输入
        print_section("输入", f"标题: {test_case['input']['title']}\n内容: {test_case['input']['content'][:100]}...")

        # 运行分析
        print("\n[正在运行分析...]")
        try:
            result = await graph.ainvoke(test_case["input"])

            # 打印结果
            print_section("投资价值",
                f"价值: {result.get('investment_value', 'N/A')}\n"
                f"置信度: {result.get('investment_confidence', 'N/A')}\n"
                f"推理: {result.get('investment_reasoning', 'N/A')}"
            )

            tokens = result.get('tokens') or []
            if tokens:
                token_list = ", ".join([f"{t['symbol']} ({t.get('name', 'N/A')})" for t in tokens])
                print_section("提取的代币", token_list)
            else:
                print_section("提取的代币", "无（因中性价值而跳过）")

            token_details = result.get('token_details') or {}
            if token_details:
                detail_lines = []
                for symbol, data in token_details.items():
                    detail_lines.append(f"{symbol}: ${data.get('price', 'N/A')} ({data.get('change_24h', 'N/A')}% 24小时)")
                print_section("代币市场数据", "\n".join(detail_lines))
            else:
                print_section("代币市场数据", "不可用")

            print_section("趋势分析", result.get('trend_analysis', 'N/A'))

            print_section("推荐",
                f"操作: {result.get('recommendation', 'N/A')}\n"
                f"风险等级: {result.get('risk_level', 'N/A')}\n"
                f"推理: {result.get('recommendation_reasoning', 'N/A')}"
            )

            # 检查错误
            if result.get('error'):
                print_section("警告", f"发生错误: {result['error']}")

            print("\n✓ 测试用例完成")

        except Exception as e:
            print_section("错误", str(e))
            import traceback
            traceback.print_exc()

    print_header("所有测试完成")


def main():
    """主入口。"""
    asyncio.run(test_graph())


if __name__ == "__main__":
    main()
