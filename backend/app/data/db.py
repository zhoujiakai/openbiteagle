"""Database session and base model.

Reference: repos/back-template/data/db.py
"""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import cfg

engine = create_async_engine(
    cfg.database.DATABASE_URL,
    echo=cfg.app.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


Base.metadata.schema = cfg.database.DATABASE_SCHEMA


async def ensure_schema() -> None:
    """Create the database schema and required extensions if they do not exist."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {cfg.database.DATABASE_SCHEMA}")
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
