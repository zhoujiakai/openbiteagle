#!/usr/bin/env python
"""Test single document embedding."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.db import AsyncSessionLocal
from app.data.vector import get_all_documents
from app.rag.embeddings import EmbeddingService
import traceback


async def main():
    service = EmbeddingService(use_mock=True)

    # Get first document
    from app.data.db import AsyncSessionLocal as DBSession
    async with DBSession() as db:
        result = await get_all_documents()
        documents = result

    if not documents:
        print("No documents found")
        return

    doc = documents[0]
    print(f"Testing with: {doc.title[:50]}...")
    print(f"Content length: {len(doc.content)} chars")
    print()

    try:
        stats = await service.process_document(doc.id)
        print(f"✅ Success!")
        print(f"  Chunks created: {stats['chunks_created']}")
        print(f"  Embedding dim: {stats['embedding_dim']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

    await service.close()


if __name__ == "__main__":
    asyncio.run(main())
