#!/usr/bin/env python
"""将 document_chunks 表从 1536 维迁移到 1024 维。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.db import AsyncSessionLocal
from app.core.config import cfg
from sqlalchemy import text


async def main():
    """删除并重建 document_chunks 表，使用新维度。"""

    schema = cfg.database.DATABASE_SCHEMA
    table_fqn = f"{schema}.document_chunks"

    async with AsyncSessionLocal() as db:
        print("正在检查当前模式...")
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
        response = input("是否删除并重建 document_chunks 表？(yes/no): ")

        if response.lower() != "yes":
            print("已取消。")
            return

        print("正在删除 document_chunks 表...")
        await db.execute(text(f"DROP TABLE IF EXISTS {table_fqn} CASCADE"))
        await db.commit()

        print("正在使用新模式重建表...")
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

        print("正在创建索引...")
        await db.execute(text(
            f"CREATE INDEX ON {table_fqn} USING ivfflat (embedding vector_cosine_ops)"
        ))
        await db.commit()

        print("迁移完成!")


if __name__ == "__main__":
    asyncio.run(main())
