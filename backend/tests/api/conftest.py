"""API 测试的固件。"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.data.db import Base
from app.models.analysis import Analysis
from app.models.news import News


@pytest_asyncio.fixture
async def async_engine():
    """创建内存 SQLite 异步引擎用于测试。"""
    from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # 将 PostgreSQL 特有类型替换为 SQLite 兼容类型
    for table in Base.metadata.tables.values():
        for column in table.columns:
            type_str = str(column.type)
            if "JSONB" in type_str or "JSON" in type_str:
                column.type = SQLiteJSON()
            elif "ARRAY" in type_str:
                from sqlalchemy import Text
                column.type = Text()

    # 仅创建本测试所需的表
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[
                    Base.metadata.tables["news"],
                    Base.metadata.tables["analysis"],
                ]
            )
        )

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncSession:
    """创建异步数据库会话用于测试。"""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def sample_news(db_session: AsyncSession) -> News:
    """创建测试用新闻样本。"""
    news = News(
        title="测试新闻标题",
        content="这是一条关于比特币和以太坊的测试新闻内容。",
        source_url="https://test.com/news/1",
    )
    db_session.add(news)
    await db_session.commit()
    yield news


@pytest_asyncio.fixture
async def sample_analysis(db_session: AsyncSession, sample_news: News) -> Analysis:
    """创建测试用分析样本。"""
    analysis = Analysis(
        news_id=sample_news.id,
        status="completed",
        investment_value="bullish",
        confidence=0.85,
        tokens={"tokens": [{"symbol": "BTC", "name": "Bitcoin"}]},
        trend_analysis="观察到正向趋势。",
        recommendation="buy",
        steps={
            "steps": [
                {"name": "investment_value", "result": {"value": "bullish"}},
                {"name": "extract_tokens", "result": {"tokens": ["BTC"]}},
            ]
        },
    )
    db_session.add(analysis)
    await db_session.commit()
    yield analysis


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> TestClient:
    """带有异步数据库会话覆盖的测试客户端。"""
    from app.main import app
    from app.api.v1.news import get_db

    # 覆盖依赖
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # 使用同步 TestClient，但带有异步数据库覆盖
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
