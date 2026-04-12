#!/usr/bin/env python3
"""Process documents and create embeddings."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.vector import get_all_documents
from app.rag.embeddings import get_embedding_service


async def main():
    """Process all documents and create embeddings."""
    print("=" * 60)
    print("Processing Documents for Embeddings")
    print("=" * 60)
    print()

    # Get all documents
    docs = await get_all_documents(limit=100)

    if not docs:
        print("❌ No documents found. Run 'python scripts/add_sample_docs.py' first")
        return

    print(f"Found {len(docs)} documents to process")
    print()

    embedding_service = get_embedding_service()

    total_chunks = 0

    for doc in docs:
        print(f"Processing: {doc.title}")

        try:
            result = await embedding_service.process_document(
                document_id=doc.id,
                chunk_size=500,
                chunk_overlap=100,
            )

            total_chunks += result["chunks_created"]
            print(f"   ✅ Created {result['chunks_created']} chunks")
            print(f"   📐 Embedding dim: {result['embedding_dim']}")
            print()

        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()

    print("=" * 60)
    print(f"✅ Processed {len(docs)} documents, created {total_chunks} chunks")
    print()
    print("Next: Run 'python scripts/test_rag.py' to test retrieval")


if __name__ == "__main__":
    asyncio.run(main())
