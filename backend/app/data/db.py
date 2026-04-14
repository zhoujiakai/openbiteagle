"""数据库会话和基础模型。

参考: repos/back-template/data/db.py
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
    """所有数据库模型的基类。"""

    pass


Base.metadata.schema = cfg.database.DATABASE_SCHEMA


async def ensure_schema() -> None:
    """如果数据库架构和所需扩展不存在，则创建它们。"""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {cfg.database.DATABASE_SCHEMA}")
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
