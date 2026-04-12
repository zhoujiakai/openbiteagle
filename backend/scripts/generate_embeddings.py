#!/usr/bin/env python
"""Generate embeddings for all documents in the knowledge base."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.db import AsyncSessionLocal
from app.data.vector import get_all_documents
from app.rag.embeddings import EmbeddingService, EMBEDDING_DIM


async def main():
    """Generate embeddings for all documents without them."""
    print(f"Embedding dimension: {EMBEDDING_DIM}")
    print()

    # Check if we should use mock
    import os
    use_mock = os.getenv("USE_MOCK_EMBEDDINGS", "false").lower() == "true"
    use_real = os.getenv("USE_REAL_EMBEDDINGS", "false").lower() == "true"

    if use_real:
        use_mock = False

    service = EmbeddingService(use_mock=use_mock)

    if service.use_mock:
        print("⚠️  Using MOCK embeddings (for testing only)")
        print("   Set USE_REAL_EMBEDDINGS=true to use real Jina API")
    else:
        print("✅ Using REAL Jina embeddings")
    print()

    # Get all documents
    from app.data.db import AsyncSessionLocal as DBSession
    async with DBSession() as db:
        result = await get_all_documents()
        documents = result

    if not documents:
        print("No documents found. Import some first:")
        print("  python scripts/import_from_rootdata.py --limit 10")
        return

    print(f"Found {len(documents)} documents in database")
    print()

    # Process each document
    success_count = 0
    error_count = 0
    skip_count = 0

    for i, doc in enumerate(documents, 1):
        print(f"[{i}/{len(documents)}] Processing: {doc.title[:50]}...")

        try:
            # Check if already has embeddings
            from app.data.db import AsyncSessionLocal
            from app.models.document import DocumentChunk
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(DocumentChunk).where(
                        DocumentChunk.document_id == doc.id
                    )
                )
                existing = result.scalars().first()

                if existing:
                    print(f"  ⏭️  Already has embeddings, skipping")
                    skip_count += 1
                    continue

            # Process document
            stats = await service.process_document(doc.id)
            print(f"  ✅ Created {stats['chunks_created']} chunks ({stats['embedding_dim']}d)")
            success_count += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            error_count += 1

        # Rate limiting for real API
        if not service.use_mock and i < len(documents):
            await asyncio.sleep(0.5)

    await service.close()

    print()
    print("=" * 50)
    print(f"Summary:")
    print(f"  ✅ Success: {success_count}")
    print(f"  ⏭️  Skipped: {skip_count}")
    print(f"  ❌ Errors:  {error_count}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
