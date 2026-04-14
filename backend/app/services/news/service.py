"""用于获取和存储新闻的新闻服务。"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import News


class NewsService:
    """新闻操作服务。

    该服务连接封装层和数据库层，
    负责新闻条目的获取、去重和存储。
    """

    def __init__(
        self,
        db_session: AsyncSession,
    ):
        """初始化服务。

        Args:
            db_session: 用于持久化的数据库会话
        """
        self.db = db_session

    async def fetch_and_store(
        self,
        items: list,
    ) -> dict:
        """将新闻条目存储到数据库。

        Args:
            items: 要存储的 NewsItem 列表

        Returns:
            包含统计信息的字典：{"new": int, "skipped": int}
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
        """根据 source_id 获取新闻。

        Args:
            source_id: 唯一来源标识（例如 "odaily-5209519"）

        Returns:
            News 对象或 None
        """
        result = await self.db.execute(
            select(News).where(News.source_id == source_id)
        )
        return result.scalar_one_or_none()

    async def get_latest(self, limit: int = 50) -> list[News]:
        """从数据库获取最新新闻。

        Args:
            limit: 最大返回条数

        Returns:
            按 published_at 降序排列的 News 对象列表
        """
        result = await self.db.execute(
            select(News)
            .order_by(News.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
