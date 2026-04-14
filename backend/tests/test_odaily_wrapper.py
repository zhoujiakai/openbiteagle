#!/usr/bin/env python3
"""OdailyWrapper 测试脚本.

Usage:
    python tests/test_odaily_wrapper.py [--limit N]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 将项目根目录添加到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.wrappers import OdailyScraper


async def main():
    parser = argparse.ArgumentParser(description="测试 OdailyWrapper")
    parser.add_argument("--limit", type=int, default=5, help="获取新闻数量")
    parser.add_argument("--headless", action="store_true", default=True, help="无头模式")
    parser.add_argument("--health", action="store_true", help="健康检查")

    args = parser.parse_args()

    # 初始化 scraper
    scraper = OdailyScraper(headless=args.headless)

    print("=" * 60)
    print(f"OdailyWrapper 测试")
    print(f"   来源: {scraper.source_name}")
    print("=" * 60)
    print()

    # 健康检查
    if args.health:
        print("健康检查...")
        is_healthy = await scraper.health_check()
        status = "正常" if is_healthy else "异常"
        print(f"   状态: {status}")
        return

    # 获取新闻列表
    print(f"获取最新 {args.limit} 条快讯...")
    print("-" * 60)

    items = await scraper.fetch_news(limit=args.limit)

    if not items:
        print("未获取到任何新闻")
        return

    print(f"成功获取 {len(items)} 条新闻\n")

    for i, item in enumerate(items, 1):
        print(f"\n[{i}] {item.title}")
        print(f"    ID: {item.id}")
        if item.publishDate:
            print(f"    时间: {item.publishDate}")
        if item.images:
            print(f"    图片: {len(item.images)} 张")
            for j, img in enumerate(item.images, 1):
                print(f"      [{j}] {img}")
        # 内容太长，只显示前200字符
        content_preview = item.content[:200] + "..." if item.content and len(item.content) > 200 else item.content
        print(f"    内容: {content_preview}")

    print()
    print("=" * 60)
    print(f"测试完成！共获取 {len(items)} 条新闻")


if __name__ == "__main__":
    asyncio.run(main())
