"""Fixtures for API tests."""

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
    """Create in-memory SQLite async engine for tests."""
    from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Replace PostgreSQL-specific types with SQLite-compatible types
    for table in Base.metadata.tables.values():
        for column in table.columns:
            type_str = str(column.type)
            if "JSONB" in type_str or "JSON" in type_str:
                column.type = SQLiteJSON()
            elif "ARRAY" in type_str:
                from sqlalchemy import Text
                column.type = Text()

    # Only create the tables we need for these tests
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
    """Create async database session for tests."""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def sample_news(db_session: AsyncSession) -> News:
    """Create a sample news item for testing."""
    news = News(
        title="Test News Title",
        content="This is a test news content about Bitcoin and Ethereum.",
        source_url="https://test.com/news/1",
    )
    db_session.add(news)
    await db_session.commit()
    yield news


@pytest_asyncio.fixture
async def sample_analysis(db_session: AsyncSession, sample_news: News) -> Analysis:
    """Create a sample analysis for testing."""
    analysis = Analysis(
        news_id=sample_news.id,
        status="completed",
        investment_value="bullish",
        confidence=0.85,
        tokens={"tokens": [{"symbol": "BTC", "name": "Bitcoin"}]},
        trend_analysis="Positive trend observed.",
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
    """Test client with async database session override."""
    from app.main import app
    from app.api.v1.news import get_db

    # Override dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Use sync TestClient but with async db override
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
