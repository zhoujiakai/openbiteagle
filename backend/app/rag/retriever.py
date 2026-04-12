"""Retriever for searching knowledge base."""

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import make_transient

from app.core.config import settings
from app.data.db import AsyncSessionLocal
from app.models.document import DocumentChunk

logger = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Similarity score between -1 and 1
    """
    if len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = sum(x * x for x in a) ** 0.5
    magnitude_b = sum(y * y for y in b) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


class Retriever:
    """Vector similarity search retriever."""

    def __init__(
        self,
        top_k: int = 3,
        threshold: float = 0.7,
    ):
        """Initialize retriever.

        Args:
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)
        """
        self.top_k = top_k
        self.threshold = threshold

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_tokens: Optional[list[str]] = None,
    ) -> list[dict]:
        """Search for similar chunks.

        Args:
            query: Search query text
            top_k: Override default top_k
            filter_tokens: Optional token symbols to filter by

        Returns:
            List of matching chunks with similarity scores
        """
        from app.rag.embeddings import get_embedding_service

        # Generate query embedding
        embedding_service = get_embedding_service()
        query_vector = await embedding_service.embed_text(query)

        k = top_k or self.top_k

        async with AsyncSessionLocal() as db:
            # Fetch all chunks with embeddings
            result = await db.execute(
                select(DocumentChunk).where(DocumentChunk.embedding.isnot(None))
            )
            chunks = result.scalars().all()

            # Detach from session
            for chunk in chunks:
                make_transient(chunk)

            # Filter by tokens if specified
            if filter_tokens:
                chunks = [
                    c for c in chunks
                    if any(token in c.tokens for token in filter_tokens)
                ]

            # Compute similarities and sort
            chunk_scores = []
            for chunk in chunks:
                emb = chunk.embedding
                if emb is not None and len(emb) > 0:
                    similarity = cosine_similarity(query_vector, emb)
                    # Convert from [-1, 1] to [0, 1] range
                    similarity = (similarity + 1) / 2
                    if similarity >= self.threshold:
                        chunk_scores.append((chunk, similarity))

            # Sort by similarity (descending)
            chunk_scores.sort(key=lambda x: x[1], reverse=True)

            # Return top k results
            results = []
            for chunk, similarity in chunk_scores[:k]:
                results.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": chunk.meta_data,
                    "similarity": similarity,
                })

            return results

    async def search_by_tokens(
        self,
        tokens: list[str],
        limit: int = 5,
    ) -> list[dict]:
        """Search chunks by mentioned tokens.

        Args:
            tokens: Token symbols to search for
            limit: Maximum results

        Returns:
            List of matching chunks
        """
        async with AsyncSessionLocal() as db:
            from sqlalchemy import or_

            conditions = [DocumentChunk.tokens.any(token) for token in tokens]
            result = await db.execute(
                select(DocumentChunk)
                .where(or_(*conditions))
                .limit(limit)
            )

            chunks = result.scalars().all()

            return [
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "tokens": chunk.tokens,
                    "meta_data": chunk.meta_data,
                }
                for chunk in chunks
            ]


# Global retriever instance
_retriever: Optional[Retriever] = None


def get_retriever(top_k: int = 3, threshold: float = 0.7) -> Retriever:
    """Get or create global retriever."""
    global _retriever
    _retriever = Retriever(top_k=top_k, threshold=threshold)
    return _retriever
