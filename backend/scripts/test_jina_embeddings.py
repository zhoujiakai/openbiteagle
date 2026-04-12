#!/usr/bin/env python
"""Test Jina Embeddings."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.embeddings import EmbeddingService, EMBEDDING_DIM


async def main():
    print(f"Embedding dimension: {EMBEDDING_DIM}")
    print()

    # Test with mock first (no API call)
    print("Testing Mock Embeddings...")
    service = EmbeddingService(use_mock=True)

    test_text = "比特币是去中心化的数字货币"
    embedding = await service.embed_text(test_text)
    print(f"Text: {test_text}")
    print(f"Dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
    print()

    # Test multiple texts
    test_texts = [
        "ARB 代币有什么用？",
        "Arbitrum 是以太坊 Layer2 扩容方案",
    ]

    embeddings = await service.embed_texts(test_texts)
    print(f"Generated {len(embeddings)} embeddings")

    # Test similarity
    import numpy as np
    a = np.array(embeddings[0])
    b = np.array(embeddings[1])
    similarity = (a @ b) / (np.linalg.norm(a) * np.linalg.norm(b))
    print(f"Similarity: {similarity:.4f}")
    print()

    print("✅ Mock Embeddings test passed!")
    print()
    print("Note: To use real Jina API:")
    print("1. Get free API key at https://jina.ai/embeddings")
    print("2. Set JINA_API_KEY in .env")
    print("3. Set use_mock=False")


if __name__ == "__main__":
    asyncio.run(main())
