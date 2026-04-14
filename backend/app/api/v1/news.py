"""新闻 API 端点。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.health import router as health_router
from app.data.db import get_db
from app.models.news import News
from app.schemas.news import NewsCreate, NewsResponse

router = APIRouter(prefix="/news", tags=["news"])


@router.post("", response_model=NewsResponse)
async def create_news(
    news_data: NewsCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建新的新闻条目。"""
    # 按 source_id 检查重复
    if news_data.source_id:
        result = await db.execute(
            select(News).where(News.source_id == news_data.source_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="News with this source_id already exists")

    news = News(**news_data.model_dump())
    db.add(news)
    await db.commit()
    await db.refresh(news)

    return news


@router.get("", response_model=list[NewsResponse])
async def list_news(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """列出新闻条目。"""
    result = await db.execute(
        select(News)
        .order_by(News.published_at.desc())
        .offset(skip)
        .limit(limit)
    )
    news_list = result.scalars().all()
    return news_list


@router.get("/{news_id}", response_model=NewsResponse)
async def get_news(
    news_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取特定新闻条目。"""
    result = await db.execute(select(News).where(News.id == news_id))
    news = result.scalar_one_or_none()

    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    return news
