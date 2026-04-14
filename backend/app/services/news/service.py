"""News service for fetching and storing news."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import News


class NewsService:
    """Service for news operations.

    This service bridges the wrapper layer and database layer,
    handling fetching, deduplication, and storage of news items.
    """

    def __init__(
        self,
        db_session: AsyncSession,
    ):
        """Initialize the service.

        Args:
            db_session: Database session for persistence
        """
        self.db = db_session

    async def fetch_and_store(
        self,
        items: list,
    ) -> dict:
        """Store news items to database.

        Args:
            items: List of NewsItem to store

        Returns:
            Dict with stats: {"new": int, "skipped": int}
        """
        new_count = 0
        skipped = 0

        for item in items:
            if not item.source_id:
                skipped += 1
                continue

            # 检查是否已存在
            existing = await self.get_by_source_id(item.source_id)
            if existing:
                skipped += 1
                continue

            # 创建新的新闻记录
            news = News(
                title=item.title,
                content=item.content,
                source_url=item.source_url,
                source_id=item.source_id,
                published_at=item.published_at,
            )

            self.db.add(news)
            new_count += 1

        # 提交更改
        await self.db.commit()

        return {
            "new": new_count,
            "skipped": skipped,
        }

    async def get_by_source_id(self, source_id: str) -> Optional[News]:
        """Get news by source_id.

        Args:
            source_id: Unique source identifier (e.g., "odaily-5209519")

        Returns:
            News object or None
        """
        result = await self.db.execute(
            select(News).where(News.source_id == source_id)
        )
        return result.scalar_one_or_none()

    async def get_latest(self, limit: int = 50) -> list[News]:
        """Get latest news from database.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of News objects ordered by published_at desc
        """
        result = await self.db.execute(
            select(News)
            .order_by(News.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
