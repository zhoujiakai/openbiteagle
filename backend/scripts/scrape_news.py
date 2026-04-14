#!/usr/bin/env python3
"""从 Odaily 抓取新闻并保存到数据库。

用法:
    python scripts/scrape_news.py [--limit N]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 将项目根目录添加到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import cfg
from app.data.db import AsyncSessionLocal, engine
from app.models.news import News
from app.services import (
    NewsItem,
    clean_title,
    is_valid_news,
    scrape_odaily_news,
)


async def save_news_item(db: AsyncSession, item: NewsItem) -> tuple[News | None, str]:
    """将新闻条目保存到数据库。

    Args:
        db: 数据库会话
        item: 要保存的新闻条目

    Returns:
        元组 (News 对象或 None, 状态: 'created'/'duplicate'/'invalid')
    """
    # 检查重复
    if item.source_id:
        result = await db.execute(
            select(News).where(News.source_id == item.source_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  ✓ 重复（已跳过）: {item.title[:50]}...")
            return existing, "duplicate"

    # 验证新闻
    if not is_valid_news(item.title, item.content):
        print(f"  ✗ 无效（已跳过）: {item.title[:50]}...")
        return None, "invalid"

    # 清理标题
    cleaned_title = clean_title(item.title)

    # 创建新闻对象
    news = News(
        title=cleaned_title,
        content=item.content,
        source_url=item.source_url,
        source_id=item.source_id,
        published_at=item.published_at,
    )

    db.add(news)
    await db.commit()
    await db.refresh(news)

    print(f"  + 已创建: {cleaned_title[:50]}...")
    return news, "created"


async def main():
    """主入口。"""
    parser = argparse.ArgumentParser(description="抓取 Odaily 新闻")
    parser.add_argument("--limit", type=int, default=50, help="最大抓取新闻数")
    parser.add_argument("--dry-run", action="store_true", help="仅获取不保存到数据库")
    args = parser.parse_args()

    print(f"正在从 Odaily 获取最多 {args.limit} 条新闻...")

    # 抓取新闻
    items = await scrape_odaily_news(limit=args.limit)

    if not items:
        print("未找到新闻条目。")
        return

    print(f"已获取 {len(items)} 条新闻。")

    if args.dry_run:
        for item in items:
            print(f"  - {item.title}")
        return

    # 保存到数据库
    print("\n正在保存到数据库...")
    created_count = 0
    duplicate_count = 0
    invalid_count = 0

    async with AsyncSessionLocal() as db:
        for item in items:
            result, status = await save_news_item(db, item)
            if status == "created":
                created_count += 1
            elif status == "duplicate":
                duplicate_count += 1
            elif status == "invalid":
                invalid_count += 1

    print(f"\n完成! 已创建: {created_count}, 重复: {duplicate_count}, 无效: {invalid_count}")


if __name__ == "__main__":
    asyncio.run(main())
