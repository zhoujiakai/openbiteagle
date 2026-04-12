#!/usr/bin/env python3
"""并发爬取性能对比测试."""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.wrappers.odaily import OdailyScraper


async def test_sequential(limit: int = 5):
    """测试顺序执行 (max_concurrent=1)."""
    print(f"\n{'='*50}")
    print(f"🐌 顺序执行 (max_concurrent=1) - {limit} 条")
    print('='*50)
    
    scraper = OdailyScraper(use_mock=False, headless=True)
    
    start = time.time()
    items = await scraper.fetch_news(limit=limit)
    elapsed = time.time() - start
    
    print(f"✅ 获取 {len(items)} 条")
    print(f"⏱️  总耗时: {elapsed:.1f} 秒")
    print(f"📊 平均每条: {elapsed/len(items):.1f} 秒")
    
    return elapsed, len(items)


async def test_concurrent(limit: int = 5, max_concurrent: int = 5):
    """测试并发执行."""
    print(f"\n{'='*50}")
    print(f"🚀 并发执行 (max_concurrent={max_concurrent}) - {limit} 条")
    print('='*50)
    
    scraper = OdailyScraper(use_mock=False, headless=True)
    
    # 修改内部的 max_concurrent 参数
    original_fetch = scraper._fetch_news_details
    
    async def concurrent_fetch(browser, news_links, limit_arg):
        return await original_fetch(browser, news_links, limit_arg, max_concurrent=max_concurrent)
    
    scraper._fetch_news_details = concurrent_fetch
    
    start = time.time()
    items = await scraper.fetch_news(limit=limit)
    elapsed = time.time() - start
    
    print(f"✅ 获取 {len(items)} 条")
    print(f"⏱️  总耗时: {elapsed:.1f} 秒")
    print(f"📊 平均每条: {elapsed/len(items):.1f} 秒")
    
    return elapsed, len(items)


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="并发爬取性能对比")
    parser.add_argument("--limit", type=int, default=10, help="测试数量")
    parser.add_argument("--concurrent", type=int, default=5, help="并发数")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("📊 Odaily 爬虫并发性能对比测试")
    print("=" * 50)
    
    # 顺序执行
    seq_time, seq_count = await test_sequential(limit=args.limit)
    
    # 等待一下
    await asyncio.sleep(2)
    
    # 并发执行
    conc_time, conc_count = await test_concurrent(limit=args.limit, max_concurrent=args.concurrent)
    
    # 对比结果
    print(f"\n{'='*50}")
    print("📈 性能对比")
    print('='*50)
    print(f"顺序执行: {seq_time:.1f} 秒 ({seq_count} 条)")
    print(f"并发执行: {conc_time:.1f} 秒 ({conc_count} 条)")
    print(f"加速比: {seq_time/conc_time:.2f}x")
    print(f"节省时间: {seq_time - conc_time:.1f} 秒")
    print('='*50)


if __name__ == "__main__":
    asyncio.run(main())
