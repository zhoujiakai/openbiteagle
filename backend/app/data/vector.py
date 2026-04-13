"""使用 pgvector 进行向量数据库操作。"""

import logging
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import make_transient

from app.data.db import AsyncSessionLocal, Base, engine
from app.models.document import Document, DocumentChunk

logger = logging.getLogger(__name__)


async def init_vector_extension() -> None:
    """在 PostgreSQL 中初始化 pgvector 扩展。"""
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension initialized")
        except Exception as e:
            logger.error(f"Failed to initialize pgvector: {e}")
            raise


async def create_tables() -> None:
    """创建向量相关的数据表。"""
    from app.data.db import ensure_schema

    await ensure_schema()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Vector tables created")


async def insert_document(
    title: str,
    content: str,
    source_url: Optional[str] = None,
    source_type: str = "manual",
    metadata: Optional[dict] = None,
) -> int:
    """向知识库中插入一篇文档。

    Args:
        title: 文档标题
        content: 文档内容
        source_url: 可选的来源 URL
        source_type: 来源类型（manual、rootdata、odaily）
        metadata: 可选的元数据字典

    Returns:
        文档 ID
    """
    async with AsyncSessionLocal() as db:
        doc = Document(
            title=title,
            content=content,
            source_url=source_url,
            source_type=source_type,
            meta_data=metadata or {},
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc.id


async def insert_chunk(
    document_id: int,
    chunk_index: int,
    content: str,
    tokens: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
) -> int:
    """插入一个文档分块。

    Args:
        document_id: 所属文档 ID
        chunk_index: 分块序号
        content: 分块内容
        tokens: 该分块中提到的代币符号
        metadata: 可选的元数据

    Returns:
        分块 ID
    """
    async with AsyncSessionLocal() as db:
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            tokens=tokens or [],
            meta_data=metadata or {},
        )
        db.add(chunk)
        await db.commit()
        await db.refresh(chunk)
        return chunk.id


async def get_document(document_id: int) -> Optional[Document]:
    """根据 ID 获取文档。

    Args:
        document_id: 文档 ID

    Returns:
        文档对象或 None（已脱离会话）
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            # 完全脱离会话
            make_transient(doc)
        return doc


async def search_by_tokens(tokens: list[str], limit: int = 5) -> list[DocumentChunk]:
    """根据提到的代币搜索分块。

    Args:
        tokens: 要搜索的代币符号列表
        limit: 最大返回数量

    Returns:
        匹配的分块列表
    """
    async with AsyncSessionLocal() as db:
        # 使用 PostgreSQL 的 overlap 操作符进行数组搜索
        from sqlalchemy import or_

        conditions = [DocumentChunk.tokens.any(token) for token in tokens]
        result = await db.execute(
            select(DocumentChunk)
            .where(or_(*conditions))
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_all_documents(limit: int = 100) -> list[Document]:
    """获取所有文档。

    Args:
        limit: 最大文档数量

    Returns:
        文档列表（已脱离会话）
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        docs = list(result.scalars().all())
        # 将所有文档完全脱离会话
        for doc in docs:
            make_transient(doc)
        return docs


async def get_document_chunks(document_id: int) -> list[DocumentChunk]:
    """获取文档的所有分块。

    Args:
        document_id: 文档 ID

    Returns:
        分块列表
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())
