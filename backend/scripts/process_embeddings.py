#!/usr/bin/env python3
"""处理文档并创建向量嵌入。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.vector import get_all_documents
from app.rag.embeddings import get_embedding_service


async def main():
    """处理所有文档并创建向量嵌入。"""
    print("=" * 60)
    print("正在处理文档以生成嵌入")
    print("=" * 60)
    print()

    # 获取所有文档
    docs = await get_all_documents(limit=100)

    if not docs:
        print("❌ 未找到文档，请先运行 'python scripts/add_sample_docs.py'")
        return

    print(f"找到 {len(docs)} 篇待处理文档")
    print()

    embedding_service = get_embedding_service()

    total_chunks = 0

    for doc in docs:
        print(f"正在处理: {doc.title}")

        try:
            result = await embedding_service.process_document(
                document_id=doc.id,
                chunk_size=500,
                chunk_overlap=100,
            )

            total_chunks += result["chunks_created"]
            print(f"   ✅ 创建了 {result['chunks_created']} 个分块")
            print(f"   📐 嵌入维度: {result['embedding_dim']}")
            print()

        except Exception as e:
            print(f"   ❌ 错误: {e}")
            print()

    print("=" * 60)
    print(f"✅ 已处理 {len(docs)} 篇文档，创建了 {total_chunks} 个分块")
    print()
    print("下一步: 运行 'python scripts/test_rag.py' 测试检索")


if __name__ == "__main__":
    asyncio.run(main())
