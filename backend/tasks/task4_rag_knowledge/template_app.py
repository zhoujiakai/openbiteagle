"""爬取 Odaily 深度文章并存入知识库 Document 表的脚本。

三步流程：
  1. 通过 Odaily REST API 抓取指定数量的深度文章链接列表
  2. 逐篇获取文章正文，读一篇存一篇，不堆积在内存中
  3. 每篇文章获取内容后立即写入 Document 表
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx

from sqlalchemy import select

from app.data.db import AsyncSessionLocal, Base, ensure_schema, engine
from app.data.logger import create_logger
from app.data.vector import insert_document
from app.models.document import Document  # noqa: F401 ensure model is registered
from app.wrappers.odaily import OdailyRestScraper


logger = create_logger("task4")

LIMIT = 100  # 抓取文章数量


async def _already_exists(source_url: str) -> bool:
    """根据 source_url 检查文章是否已存在于 Document 表。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document.id).where(Document.source_url == source_url)
        )
        return result.scalar() is not None


async def _fetch_single_content(article) -> str:
    """获取单篇文章的完整正文，失败返回空字符串。"""
    content = article.content or ""

    if not content and article.link:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(article.link, headers={"Accept": "application/json"})
                data = resp.json()
                raw = data.get("data", {}).get("content", "")
                if raw:
                    content = re.sub(r"<[^>]+>", "", raw).strip()
        except Exception as e:
            logger.error(f"获取详情失败 [{article.link}]: {e}")

    return content


async def main():
    # 建表
    await ensure_schema()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scraper = OdailyRestScraper()

    # 第一步：获取文章链接
    logger.info(f"获取 {LIMIT} 篇深度文章...")
    articles = await scraper.fetch_depth_articles(limit=LIMIT)
    if not articles:
        logger.warning("未获取到任何文章")
        return

    # 第二、三步：逐篇获取内容并立即入库
    saved, skipped = 0, 0
    for i, article in enumerate(articles, 1):
        if article.link and await _already_exists(article.link):
            skipped += 1
            continue

        content = await _fetch_single_content(article)
        if not content:
            skipped += 1
            continue

        metadata = {}
        if article.id:
            metadata["source_id"] = article.id
        if article.publishDate:
            metadata["published_at"] = article.publishDate
        if article.images:
            metadata["images"] = article.images

        doc_id = await insert_document(
            title=article.title,
            content=content,
            source_url=article.link,
            source_type="odaily-deep",
            metadata=metadata,
        )
        saved += 1
        logger.info(f"  [{i}/{len(articles)}] doc_id={doc_id}  {article.title}")

    logger.info(f"完成：写入 {saved} 篇，跳过 {skipped} 篇")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
