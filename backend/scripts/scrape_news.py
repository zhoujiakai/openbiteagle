#!/usr/bin/env python3
"""Scrape news from Odaily and save to database.

Usage:
    python scripts/scrape_news.py [--limit N]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
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
    """Save a news item to database.

    Args:
        db: Database session
        item: News item to save

    Returns:
        Tuple of (News object or None, status: 'created'/'duplicate'/'invalid')
    """
    # Check for duplicate
    if item.source_id:
        result = await db.execute(
            select(News).where(News.source_id == item.source_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  ✓ Duplicate (skipped): {item.title[:50]}...")
            return existing, "duplicate"

    # Validate news
    if not is_valid_news(item.title, item.content):
        print(f"  ✗ Invalid (skipped): {item.title[:50]}...")
        return None, "invalid"

    # Clean title
    cleaned_title = clean_title(item.title)

    # Create news object
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

    print(f"  + Created: {cleaned_title[:50]}...")
    return news, "created"


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Scrape Odaily news")
    parser.add_argument("--limit", type=int, default=50, help="Max number of news to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but don't save to database")
    args = parser.parse_args()

    print(f"Fetching up to {args.limit} news items from Odaily...")

    # Scrape news
    items = await scrape_odaily_news(limit=args.limit)

    if not items:
        print("No news items found.")
        return

    print(f"Fetched {len(items)} news items.")

    if args.dry_run:
        for item in items:
            print(f"  - {item.title}")
        return

    # Save to database
    print("\nSaving to database...")
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

    print(f"\nDone! Created: {created_count}, Duplicates: {duplicate_count}, Invalid: {invalid_count}")


if __name__ == "__main__":
    asyncio.run(main())
