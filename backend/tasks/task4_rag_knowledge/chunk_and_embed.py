"""将数据库中的 Document 进行分块和向量化，存入 document_chunks 表。

流程：
  1. 查询所有尚未生成嵌入分块的 Document
  2. 对每篇文档进行文本分块
  3. 调用 Jina Embeddings API 批量生成向量
  4. 将 DocumentChunk 记录写入数据库
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, func

from app.data.db import AsyncSessionLocal, Base, ensure_schema, engine
from app.data.logger import create_logger
from app.data.vector import get_document_chunks
from app.models.document import Document, DocumentChunk  # noqa: F401
from app.rag.embeddings import get_embedding_service

logger = create_logger("task4_embed")

# 每批处理的文档数量
BATCH_SIZE = 10

# 最多处理的文档数量，0 表示处理全部
LIMIT = 20


async def _get_unembedded_doc_ids(limit: int = 0) -> list[int]:
    """获取尚未生成嵌入分块的文档 ID 列表。

    通过左连接查找没有对应 DocumentChunk 记录的 Document。

    Args:
        limit: 最大返回数量，0 表示不限制
    """
    async with AsyncSessionLocal() as session:
        # 子查询：已有分块的 document_id
        chunked_ids = select(DocumentChunk.document_id).distinct()
        # 主查询：不在上述子查询中的文档
        stmt = (
            select(Document.id)
            .where(Document.id.notin_(chunked_ids))
            .order_by(Document.created_at.desc())
        )
        if limit > 0:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def _process_document(doc_id: int) -> dict:
    """处理单篇文档：分块 -> 向量化 -> 存储。

    Args:
        doc_id: 文档 ID

    Returns:
        处理结果统计
    """
    embedding_service = get_embedding_service()

    try:
        result = await embedding_service.process_document(doc_id)
        logger.info(
            f"  doc_id={doc_id}: {result['chunks_created']} 个分块, "
            f"向量维度={result['embedding_dim']}"
        )
        return {"doc_id": doc_id, "status": "ok", **result}
    except Exception as e:
        logger.error(f"  doc_id={doc_id} 处理失败: {e}")
        return {"doc_id": doc_id, "status": "error", "error": str(e)}


async def main():
    # 建表
    await ensure_schema()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 获取未生成嵌入的文档 ID
    doc_ids = await _get_unembedded_doc_ids(limit=LIMIT)
    if not doc_ids:
        logger.info("没有需要处理的文档（所有文档已有嵌入分块）")
        await engine.dispose()
        return

    logger.info(f"共 {len(doc_ids)} 篇文档需要生成嵌入分块" + (f"（限制 {LIMIT} 篇）" if LIMIT else ""))

    # 分批处理，避免内存和 API 限流问题
    total_ok = 0
    total_error = 0
    total_chunks = 0

    for batch_start in range(0, len(doc_ids), BATCH_SIZE):
        batch_ids = doc_ids[batch_start:batch_start + BATCH_SIZE]
        logger.info(
            f"处理批次 {batch_start // BATCH_SIZE + 1}: "
            f"doc_id {batch_ids[0]}-{batch_ids[-1]}"
        )

        for doc_id in batch_ids:
            result = await _process_document(doc_id)
            if result["status"] == "ok":
                total_ok += 1
                total_chunks += result["chunks_created"]
            else:
                total_error += 1

    # 关闭嵌入服务 HTTP 客户端
    embedding_service = get_embedding_service()
    await embedding_service.close()

    logger.info(
        f"完成：成功 {total_ok} 篇，失败 {total_error} 篇，"
        f"共生成 {total_chunks} 个分块"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
