#!/usr/bin/env python3
"""并发爬取性能对比测试.

使用 OdailyRestScraper 进行 API 请求性能测试。
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.wrappers.odaily import OdailyRestScraper


async def test_fetch(limit: int = 20):
    """测试 REST API 获取性能."""
    print(f"\n{'='*50}")
    print(f"REST API 获取 - {limit} 条")
    print('='*50)

    scraper = OdailyRestScraper()

    start = time.time()
    items = await scraper.fetch_news(limit=limit)
    elapsed = time.time() - start

    print(f"获取 {len(items)} 条")
    print(f"总耗时: {elapsed:.1f} 秒")
    if items:
        print(f"平均每条: {elapsed/len(items):.2f} 秒")

    return elapsed, len(items)


async def test_fetch_depth(limit: int = 20):
    """测试深度文章获取."""
    print(f"\n{'='*50}")
    print(f"深度文章获取 - {limit} 条")
    print('='*50)

    scraper = OdailyRestScraper()

    start = time.time()
    items = await scraper.fetch_depth_articles(limit=limit)
    elapsed = time.time() - start

    print(f"获取 {len(items)} 条")
    print(f"总耗时: {elapsed:.1f} 秒")
    if items:
        print(f"平均每条: {elapsed/len(items):.2f} 秒")

    return elapsed, len(items)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="并发爬取性能测试")
    parser.add_argument("--limit", type=int, default=20, help="测试数量")

    args = parser.parse_args()

    print("=" * 50)
    print("Odaily REST API 性能测试")
    print("=" * 50)

    # 快讯获取
    news_time, news_count = await test_fetch(limit=args.limit)

    # 深度文章获取
    depth_time, depth_count = await test_fetch_depth(limit=args.limit)

    # 汇总
    print(f"\n{'='*50}")
    print("测试汇总")
    print('='*50)
    print(f"快讯: {news_time:.1f} 秒 ({news_count} 条)")
    print(f"深度文章: {depth_time:.1f} 秒 ({depth_count} 条)")
    print('='*50)


if __name__ == "__main__":
    asyncio.run(main())
