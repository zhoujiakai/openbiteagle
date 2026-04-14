#!/usr/bin/env python3
"""OdailyNewsService 测试脚本.

Usage:
    python scripts/test_odaily_service.py [--limit N] [--real]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 将项目根目录添加到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.db import AsyncSessionLocal
from app.services.news import NewsService


async def main():
    parser = argparse.ArgumentParser(description="测试 OdailyNewsService")
    parser.add_argument("--limit", type=int, default=5, help="获取新闻数量")
    parser.add_argument("--real", action="store_true", help="使用真实爬虫")
    parser.add_argument("--latest", type=int, help="从数据库获取最新 N 条")

    args = parser.parse_args()

    use_mock = not args.real

    print("=" * 60)
    print(f"📰 OdailyNewsService 测试")
    print(f"   模式: {'Mock 数据' if use_mock else '真实爬虫'}")
    print("=" * 60)
    print()

    async with AsyncSessionLocal() as db:
        service = NewsService(db)

        # 获取数据库中的最新新闻
        if args.latest is not None:
            print(f"📂 从数据库获取最新 {args.latest} 条新闻...")
            print("-" * 60)
            items = await service.get_latest(limit=args.latest)

            if items:
                print(f"✅ 找到 {len(items)} 条新闻\n")
                for item in items:
                    print(f"  [{item.id}] {item.title}")
                    print(f"      来源: {item.source_id}")
                    print(f"      时间: {item.published_at}")
                    if item.images:
                        print(f"      图片: {len(item.images.get('images', []))} 张")
                print()
            else:
                print("  数据库中没有新闻\n")

        # 爬取并存储
        else:
            print(f"🔥 爬取并存储最新 {args.limit} 条新闻...")
            print("-" * 60)

            stats = await service.fetch_and_store(limit=args.limit)

            print(f"✅ 完成!")
            print(f"   获取: {stats['fetched']} 条")
            print(f"   新增: {stats['new']} 条")
            print(f"   跳过: {stats['skipped']} 条")
            print()

            # 查询最新的一条
            if stats['new'] > 0:
                print("📂 最新存储的新闻:")
                latest = await service.get_latest(limit=1)
                if latest:
                    item = latest[0]
                    print(f"   标题: {item.title}")
                    print(f"   来源ID: {item.source_id}")
                    if item.images:
                        imgs = item.images.get('images', [])
                        if imgs:
                            print(f"   图片: {len(imgs)} 张")
                            print(f"   第一张: {imgs[0]['url'][:60]}...")

    print()
    print("=" * 60)
    print("✅ 测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
