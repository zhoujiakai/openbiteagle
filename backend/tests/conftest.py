"""Pytest configuration."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.data.db import Base


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_openai_api_key(monkeypatch):
    """Set mock OpenAI API key for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-testing")
    return "test-key-for-testing"


@pytest.fixture
def mock_settings(monkeypatch, tmp_path):
    """Set mock settings for tests."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("RABBITMQ_URL", "")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    return True


@pytest_asyncio.fixture
async def async_engine():
    """Create async engine for tests."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncSession:
    """Create async session for tests."""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()
