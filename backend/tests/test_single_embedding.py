#!/usr/bin/env python
"""测试单文档嵌入。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.db import AsyncSessionLocal
from app.data.vector import get_all_documents
from app.rag.embeddings import EmbeddingService
import traceback


async def main():
    service = EmbeddingService()

    # 获取第一个文档
    from app.data.db import AsyncSessionLocal as DBSession
    async with DBSession() as db:
        result = await get_all_documents()
        documents = result

    if not documents:
        print("未找到文档")
        return

    doc = documents[0]
    print(f"测试文档: {doc.title[:50]}...")
    print(f"内容长度: {len(doc.content)} 字符")
    print()

    try:
        stats = await service.process_document(doc.id)
        print(f"✅ 成功！")
        print(f"  创建分块数: {stats['chunks_created']}")
        print(f"  嵌入维度: {stats['embedding_dim']}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()

    await service.close()


if __name__ == "__main__":
    asyncio.run(main())
