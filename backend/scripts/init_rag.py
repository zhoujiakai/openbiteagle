#!/usr/bin/env python3
"""Initialize RAG knowledge base with pgvector."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.config import settings
from app.data.db import engine
from app.data.vector import create_tables, init_vector_extension


async def main():
    """Initialize RAG knowledge base."""
    print("=" * 60)
    print("RAG Knowledge Base Initialization")
    print("=" * 60)
    print(f"Database: {settings.DATABASE_URL}")
    print()

    # Initialize pgvector extension
    print("1. Initializing pgvector extension...")
    try:
        await init_vector_extension()
    except Exception as e:
        print(f"   ⚠️  pgvector extension: {e}")
        print("   Make sure pgvector is installed in PostgreSQL")
        return

    # Create tables
    print("\n2. Creating vector tables...")
    try:
        await create_tables()
    except Exception as e:
        print(f"   ❌ Error creating tables: {e}")
        return

    # Verify embedding column
    print("\n3. Verifying pgvector setup...")
    async with engine.begin() as conn:
        try:
            result = await conn.execute(
                text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'document_chunks'")
            )
            columns = result.fetchall()
            print(f"   Columns in document_chunks: {[c[0] for c in columns]}")

            # Check for embedding column
            has_embedding = any(c[0] == "embedding" for c in columns)
            if has_embedding:
                print("   ✅ Embedding column found")
            else:
                print("   ⚠️  Embedding column not found - will need to add manually")
        except Exception as e:
            print(f"   ⚠️  Could not verify: {e}")

    print()
    print("=" * 60)
    print("✅ RAG knowledge base initialized!")
    print()
    print("Next steps:")
    print("1. Add documents: python scripts/add_sample_docs.py")
    print("2. Process embeddings: python scripts/process_embeddings.py")
    print("3. Test retrieval: python scripts/test_rag.py")


if __name__ == "__main__":
    asyncio.run(main())
