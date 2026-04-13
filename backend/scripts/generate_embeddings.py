#!/usr/bin/env python
"""为知识库中的所有文档生成向量嵌入。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.db import AsyncSessionLocal
from app.data.vector import get_all_documents
from app.rag.embeddings import EmbeddingService, EMBEDDING_DIM


async def main():
    """为所有未生成嵌入的文档生成向量嵌入。"""
    print(f"嵌入维度: {EMBEDDING_DIM}")
    print()

    # 检查是否使用模拟嵌入
    import os
    use_mock = os.getenv("USE_MOCK_EMBEDDINGS", "false").lower() == "true"
    use_real = os.getenv("USE_REAL_EMBEDDINGS", "false").lower() == "true"

    if use_real:
        use_mock = False

    service = EmbeddingService(use_mock=use_mock)

    if service.use_mock:
        print("⚠️  使用模拟嵌入（仅用于测试）")
        print("   设置 USE_REAL_EMBEDDINGS=true 以使用真实的 Jina API")
    else:
        print("✅ 使用真实的 Jina 嵌入")
    print()

    # 获取所有文档
    from app.data.db import AsyncSessionLocal as DBSession
    async with DBSession() as db:
        result = await get_all_documents()
        documents = result

    if not documents:
        print("未找到文档，请先导入:")
        print("  python scripts/import_from_rootdata.py --limit 10")
        return

    print(f"数据库中找到 {len(documents)} 篇文档")
    print()

    # 处理每个文档
    success_count = 0
    error_count = 0
    skip_count = 0

    for i, doc in enumerate(documents, 1):
        print(f"[{i}/{len(documents)}] 正在处理: {doc.title[:50]}...")

        try:
            # 检查是否已有嵌入
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
                    print(f"  ⏭️  已有嵌入，跳过")
                    skip_count += 1
                    continue

            # 处理文档
            stats = await service.process_document(doc.id)
            print(f"  ✅ 创建了 {stats['chunks_created']} 个分块 ({stats['embedding_dim']}d)")
            success_count += 1

        except Exception as e:
            print(f"  ❌ 错误: {e}")
            error_count += 1

        # 真实 API 的速率限制
        if not service.use_mock and i < len(documents):
            await asyncio.sleep(0.5)

    await service.close()

    print()
    print("=" * 50)
    print(f"汇总:")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ⏭️  跳过: {skip_count}")
    print(f"  ❌ 错误:  {error_count}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
