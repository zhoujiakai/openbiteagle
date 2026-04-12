"""Embedding service for vectorizing text."""

import hashlib
import logging
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.data.vector import insert_chunk
from app.models.document import Document

logger = logging.getLogger(__name__)

# Embedding dimensions for Jina jina-embeddings-v3
EMBEDDING_DIM = 1024

# Jina API endpoint
JINA_API_URL = "https://api.jina.ai/v1/embeddings"


class MockEmbeddings:
    """Mock embedding service for testing without API."""

    def __init__(self, dimension: int = EMBEDDING_DIM):
        self.dimension = dimension

    async def aembed_query(self, text: str) -> list[float]:
        """Generate mock embedding based on text hash."""
        hash_val = int(hashlib.sha256(text.encode()).hexdigest(), 16)
        vector = []
        for i in range(self.dimension):
            val = ((hash_val >> (i % 64)) & 0xFFFF) / 32768.0 - 1.0
            vector.append(val)
        return vector

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate mock embeddings for multiple texts."""
        return [await self.aembed_query(text) for text in texts]

    def sync_embed(self, text: str) -> list[float]:
        """Synchronous version for SQL query construction."""
        hash_val = int(hashlib.sha256(text.encode()).hexdigest(), 16)
        vector = []
        for i in range(self.dimension):
            val = ((hash_val >> (i % 64)) & 0xFFFF) / 32768.0 - 1.0
            vector.append(val)
        return vector


class JinaEmbeddings:
    """Jina Embeddings client using HTTP API."""

    def __init__(self, model: str = "jina-embeddings-v3", api_key: str = None):
        self.model = model
        self.api_key = api_key or "jina_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # Free tier placeholder
        self.api_url = JINA_API_URL
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def aembed_query(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = await self.client.post(
            self.api_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            json={
                "model": self.model,
                "input": [text],
                "encoding_format": "float",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        # Batch requests (max 8 texts per request for Jina free tier)
        batch_size = 8
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.client.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model,
                    "input": batch,
                    "encoding_format": "float",
                },
            )
            response.raise_for_status()
            data = response.json()
            batch_embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()


class EmbeddingService:
    """Service for generating and storing embeddings."""

    def __init__(self, model: str = None, use_mock: bool = False):
        """Initialize embedding service.

        Args:
            model: Jina embedding model name (default from settings)
            use_mock: Force use of mock embeddings for testing
        """
        self._embeddings: Optional[JinaEmbeddings | MockEmbeddings] = None
        self.model = model or settings.JINA_EMBEDDING_MODEL
        # Use mock if explicitly requested or no API key configured
        self.use_mock = use_mock or not settings.JINA_API_KEY

    @property
    def embeddings(self) -> JinaEmbeddings | MockEmbeddings:
        """Get or create embeddings instance."""
        if self._embeddings is None:
            if self.use_mock:
                logger.info("Using mock embeddings for testing")
                self._embeddings = MockEmbeddings()
            else:
                logger.info(f"Using Jina embeddings: {self.model}")
                self._embeddings = JinaEmbeddings(
                    model=self.model,
                    api_key=settings.JINA_API_KEY,
                )
        return self._embeddings

    async def close(self):
        """Close the embedding service."""
        if self._embeddings and isinstance(self._embeddings, JinaEmbeddings):
            await self._embeddings.close()

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        result = await self.embeddings.aembed_query(text)
        return result

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        results = await self.embeddings.aembed_documents(texts)
        return results

    def _split_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
        """Split text into chunks with overlap.

        Args:
            text: Text to split
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            # Try to break at sentence boundary
            if end < len(text):
                for sep in [". ", "! ", "? ", "\n\n", "\n"]:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep != -1:
                        end = last_sep + len(sep)
                        break

            chunks.append(text[start:end].strip())
            new_start = end - chunk_overlap
            if new_start <= start:
                start = end
            else:
                start = new_start

        return [c for c in chunks if c]

    async def process_document(
        self,
        document_id: int,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ) -> dict:
        """Split document into chunks and create embeddings.

        Args:
            document_id: Document ID to process
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks

        Returns:
            Dict with processing stats
        """
        from app.data.db import AsyncSessionLocal
        from app.data.vector import get_document
        from app.models.document import DocumentChunk
        from pgvector.sqlalchemy import Vector

        doc = await get_document(document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        chunks = self._split_text(doc.content, chunk_size, chunk_overlap)
        logger.info(f"Split document {document_id} into {len(chunks)} chunks")

        embedding_vectors = await self.embed_texts(chunks)

        async with AsyncSessionLocal() as db:
            for i, (chunk, embedding) in enumerate(zip(chunks, embedding_vectors)):
                chunk_record = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk,
                    embedding=embedding,
                )
                db.add(chunk_record)

            await db.commit()

        return {
            "document_id": document_id,
            "chunks_created": len(chunks),
            "embedding_dim": len(embedding_vectors[0]) if embedding_vectors else 0,
        }


# Global embedding service instance
_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create global embedding service."""
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service
