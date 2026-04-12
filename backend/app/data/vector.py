"""Vector database operations using pgvector."""

import logging
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, make_transient

from app.data.db import AsyncSessionLocal, Base, engine
from app.models.document import Document, DocumentChunk

logger = logging.getLogger(__name__)


async def init_vector_extension() -> None:
    """Initialize pgvector extension in PostgreSQL."""
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("✅ pgvector extension initialized")
        except Exception as e:
            logger.error(f"Failed to initialize pgvector: {e}")
            raise


async def create_tables() -> None:
    """Create vector-related tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Vector tables created")


async def insert_document(
    title: str,
    content: str,
    source_url: Optional[str] = None,
    source_type: str = "manual",
    metadata: Optional[dict] = None,
) -> int:
    """Insert a document into the knowledge base.

    Args:
        title: Document title
        content: Document content
        source_url: Optional source URL
        source_type: Source type (manual, rootdata, odaily)
        metadata: Optional metadata dictionary

    Returns:
        Document ID
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
    """Insert a document chunk.

    Args:
        document_id: Parent document ID
        chunk_index: Chunk sequence number
        content: Chunk content
        tokens: Token symbols mentioned in this chunk
        metadata: Optional metadata

    Returns:
        Chunk ID
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
    """Get a document by ID.

    Args:
        document_id: Document ID

    Returns:
        Document object or None (detached from session)
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            # Completely detach from session
            make_transient(doc)
        return doc


async def search_by_tokens(tokens: list[str], limit: int = 5) -> list[DocumentChunk]:
    """Search chunks by mentioned tokens.

    Args:
        tokens: List of token symbols to search for
        limit: Maximum results

    Returns:
        List of matching chunks
    """
    async with AsyncSessionLocal() as db:
        # Use PostgreSQL overlap operator for array search
        from sqlalchemy import or_

        conditions = [DocumentChunk.tokens.any(token) for token in tokens]
        result = await db.execute(
            select(DocumentChunk)
            .where(or_(*conditions))
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_all_documents(limit: int = 100) -> list[Document]:
    """Get all documents.

    Args:
        limit: Maximum number of documents

    Returns:
        List of documents (detached from session)
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        docs = list(result.scalars().all())
        # Completely detach all from session
        for doc in docs:
            make_transient(doc)
        return docs


async def get_document_chunks(document_id: int) -> list[DocumentChunk]:
    """Get all chunks for a document.

    Args:
        document_id: Document ID

    Returns:
        List of chunks
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())
