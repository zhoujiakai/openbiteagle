#!/usr/bin/env python3
"""使用 pgvector 初始化 RAG 知识库。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.config import cfg
from app.data.db import engine
from app.data.vector import create_tables, init_vector_extension


async def main():
    """初始化 RAG 知识库。"""
    print("=" * 60)
    print("RAG 知识库初始化")
    print("=" * 60)
    print(f"数据库: {cfg.database.DATABASE_URL}")
    print()

    # 初始化 pgvector 扩展
    print("1. 正在初始化 pgvector 扩展...")
    try:
        await init_vector_extension()
    except Exception as e:
        print(f"   ⚠️  pgvector 扩展: {e}")
        print("   请确保 PostgreSQL 中已安装 pgvector")
        return

    # 创建表
    print("\n2. 正在创建向量表...")
    try:
        await create_tables()
    except Exception as e:
        print(f"   ❌ 创建表出错: {e}")
        return

    # 验证嵌入列
    print("\n3. 正在验证 pgvector 设置...")
    async with engine.begin() as conn:
        try:
            result = await conn.execute(
                text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'document_chunks'")
            )
            columns = result.fetchall()
            print(f"   document_chunks 中的列: {[c[0] for c in columns]}")

            # 检查嵌入列
            has_embedding = any(c[0] == "embedding" for c in columns)
            if has_embedding:
                print("   ✅ 找到嵌入列")
            else:
                print("   ⚠️  未找到嵌入列 - 需要手动添加")
        except Exception as e:
            print(f"   ⚠️  无法验证: {e}")

    print()
    print("=" * 60)
    print("✅ RAG 知识库已初始化!")
    print()
    print("下一步:")
    print("1. 添加文档: python scripts/add_sample_docs.py")
    print("2. 处理嵌入: python scripts/process_embeddings.py")
    print("3. 测试检索: python scripts/test_rag.py")


if __name__ == "__main__":
    asyncio.run(main())
