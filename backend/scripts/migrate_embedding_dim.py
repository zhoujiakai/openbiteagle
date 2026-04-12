#!/usr/bin/env python
"""Migrate document_chunks table from 1536 to 1024 dimensions."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.db import AsyncSessionLocal
from app.core.config import settings
from sqlalchemy import text


async def main():
    """Drop and recreate document_chunks table with new dimensions."""

    schema = settings.DATABASE_SCHEMA
    table_fqn = f"{schema}.document_chunks"

    async with AsyncSessionLocal() as db:
        print("Current schema check...")
        result = await db.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = :schema
            AND table_name = 'document_chunks'
            AND column_name = 'embedding'
        """), {"schema": schema})
        for row in result:
            print(f"  {row.column_name}: {row.data_type}")

        print()
        response = input("Drop and recreate document_chunks table? (yes/no): ")

        if response.lower() != "yes":
            print("Aborted.")
            return

        print("Dropping document_chunks table...")
        await db.execute(text(f"DROP TABLE IF EXISTS {table_fqn} CASCADE"))
        await db.commit()

        print("Recreating table with new schema...")
        await db.execute(text(f"""
            CREATE TABLE {table_fqn} (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding VECTOR(1024),
                meta_data JSONB DEFAULT '{{}}',
                tokens VARCHAR[] DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await db.commit()

        print("Creating index...")
        await db.execute(text(
            f"CREATE INDEX ON {table_fqn} USING ivfflat (embedding vector_cosine_ops)"
        ))
        await db.commit()

        print("Migration complete!")


if __name__ == "__main__":
    asyncio.run(main())
