#!/usr/bin/env python3
"""OdailyWrapper 测试脚本.

Usage:
    python scripts/test_odaily_wrapper.py [--limit N] [--real]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.wrappers import OdailyScraper


async def main():
    parser = argparse.ArgumentParser(description="测试 OdailyWrapper")
    parser.add_argument("--limit", type=int, default=5, help="获取新闻数量")
    parser.add_argument("--real", action="store_true", help="使用真实爬虫（需要 Playwright）")
    parser.add_argument("--headless", action="store_true", default=True, help="无头模式")
    parser.add_argument("--detail", type=str, help="获取指定新闻详情")
    parser.add_argument("--health", action="store_true", help="健康检查")

    args = parser.parse_args()

    # 初始化 scraper
    use_mock = not args.real
    scraper = OdailyScraper(use_mock=use_mock, headless=args.headless)

    print("=" * 60)
    print(f"📰 OdailyWrapper 测试")
    print(f"   模式: {'Mock 数据' if use_mock else '真实爬虫'}")
    print(f"   来源: {scraper.source_name}")
    print("=" * 60)
    print()

    # 健康检查
    if args.health:
        print("🔍 健康检查...")
        is_healthy = await scraper.health_check()
        status = "✅ 正常" if is_healthy else "❌ 异常"
        print(f"   状态: {status}")
        return

    # 获取详情
    if args.detail:
        print(f"📄 获取新闻详情: {args.detail}")
        print("-" * 60)
        item = await scraper.fetch_news_detail(args.detail)
        if item:
            print(f"标题: {item.title}")
            print(f"内容: {item.content}")
            print(f"来源: {item.source_url}")
            print(f"ID: {item.source_id}")
            print(f"时间: {item.published_at}")
        else:
            print("❌ 未找到该新闻")
        return

    # 获取新闻列表
    print(f"📋 获取最新 {args.limit} 条快讯...")
    print("-" * 60)

    items = await scraper.fetch_news(limit=args.limit)

    if not items:
        print("❌ 未获取到任何新闻")
        return

    print(f"✅ 成功获取 {len(items)} 条新闻\n")

    for i, item in enumerate(items, 1):
        print(f"\n[{i}] {item.title}")
        print(f"    来源: {item.source_url}")
        print(f"    ID: {item.source_id}")
        if item.published_at:
            print(f"    时间: {item.published_at.strftime('%Y-%m-%d %H:%M')}")
        if item.images:
            print(f"    图片: {len(item.images)} 张")
            for j, img in enumerate(item.images, 1):
                print(f"      [{j}] {img}")
        # 内容太长，只显示前200字符
        content_preview = item.content[:200] + "..." if item.content and len(item.content) > 200 else item.content
        print(f"    内容: {content_preview}")

    print()
    print("=" * 60)
    print(f"✅ 测试完成！共获取 {len(items)} 条新闻")


if __name__ == "__main__":
    asyncio.run(main())
