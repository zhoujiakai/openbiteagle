"""爬取 Odaily 快讯并存入 PostgreSQL 的脚本。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.data.db import AsyncSessionLocal, Base, ensure_schema, engine
from app.data.logger import create_logger
from app.models.news import News  # noqa: F401 ensure model is registered
from sqlalchemy import select

from odaily_rest_scraper import OdailyRestScraper

logger = create_logger("Odaily入库脚本")


async def save_to_db(items) -> int:
    """将新闻条目存入数据库，跳过已存在的记录。

    Args:
        items: NewsItem 列表

    Returns:
        新插入的记录数
    """
    saved = 0
    async with AsyncSessionLocal() as session:
        for item in items:
            if not item.id:
                continue
            # 按 source_id 去重
            exists = await session.execute(
                select(News.source_id).where(News.source_id == item.id)
            )
            if exists.scalar():
                continue

            row = News(
                source_id=item.id,
                title=item.title,
                content=item.content,
                images=item.images,
                isImportant=item.isImportant,
                publishTimestamp=item.publishTimestamp,
                publishDate=item.publishDate,
                sourceUrl=item.sourceUrl,
                link=item.link,
            )
            session.add(row)
            saved += 1
            logger.info(f"新增: [{item.publishDate}] {item.title[:40]}")

        if saved:
            await session.commit()
    return saved


async def main():
    scraper = OdailyRestScraper()

    # 建表
    await ensure_schema()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("表结构就绪")

    # 爬取
    logger.info("开始爬取 Odaily 快讯")
    items = await scraper.fetch_news(limit=40)
    logger.info(f"爬取到 {len(items)} 条")

    if not items:
        logger.warning("未爬取到任何数据")
        return

    # 入库
    saved = await save_to_db(items)
    logger.info(f"新增 {saved} 条，跳过 {len(items) - saved} 条（已存在）")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
