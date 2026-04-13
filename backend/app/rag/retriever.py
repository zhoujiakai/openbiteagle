"""知识库检索器。"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import make_transient

from app.data.db import AsyncSessionLocal
from app.models.document import DocumentChunk

logger = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。

    Args:
        a: 第一个向量
        b: 第二个向量

    Returns:
        相似度分数，范围 [-1, 1]
    """
    if len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = sum(x * x for x in a) ** 0.5
    magnitude_b = sum(y * y for y in b) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


class Retriever:
    """基于向量相似度的检索器。"""

    def __init__(
        self,
        top_k: int = 3,
        threshold: float = 0.7,
    ):
        """初始化检索器。

        Args:
            top_k: 返回的最大结果数
            threshold: 最低相似度阈值（0-1）
        """
        self.top_k = top_k
        self.threshold = threshold

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_tokens: Optional[list[str]] = None,
    ) -> list[dict]:
        """检索与查询相似的文档分块。

        Args:
            query: 查询文本
            top_k: 覆盖默认的 top_k 值
            filter_tokens: 可选的代币符号过滤列表

        Returns:
            匹配分块列表，包含相似度分数
        """
        from app.rag.embeddings import get_embedding_service

        # 生成查询文本的嵌入向量
        embedding_service = get_embedding_service()
        query_vector = await embedding_service.embed_text(query)

        k = top_k or self.top_k

        async with AsyncSessionLocal() as db:
            # 获取所有已生成嵌入的分块
            result = await db.execute(
                select(DocumentChunk).where(DocumentChunk.embedding.isnot(None))
            )
            chunks = result.scalars().all()

            # 从会话中分离对象
            for chunk in chunks:
                make_transient(chunk)

            # 如果指定了代币符号，进行过滤
            if filter_tokens:
                chunks = [
                    c for c in chunks
                    if any(token in c.tokens for token in filter_tokens)
                ]

            # 计算相似度并排序
            chunk_scores = []
            for chunk in chunks:
                emb = chunk.embedding
                if emb is not None and len(emb) > 0:
                    similarity = cosine_similarity(query_vector, emb)
                    # 将范围从 [-1, 1] 转换为 [0, 1]
                    similarity = (similarity + 1) / 2
                    if similarity >= self.threshold:
                        chunk_scores.append((chunk, similarity))

            # 按相似度降序排列
            chunk_scores.sort(key=lambda x: x[1], reverse=True)

            # 返回前 k 个结果
            results = []
            for chunk, similarity in chunk_scores[:k]:
                results.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": chunk.meta_data,
                    "similarity": similarity,
                })

            return results

    async def search_by_tokens(
        self,
        tokens: list[str],
        limit: int = 5,
    ) -> list[dict]:
        """根据提及的代币符号检索文档分块。

        Args:
            tokens: 待搜索的代币符号列表
            limit: 最大返回数

        Returns:
            匹配分块列表
        """
        async with AsyncSessionLocal() as db:
            from sqlalchemy import or_

            conditions = [DocumentChunk.tokens.any(token) for token in tokens]
            result = await db.execute(
                select(DocumentChunk)
                .where(or_(*conditions))
                .limit(limit)
            )

            chunks = result.scalars().all()

            return [
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "tokens": chunk.tokens,
                    "meta_data": chunk.meta_data,
                }
                for chunk in chunks
            ]


# 全局检索器实例
_retriever: Optional[Retriever] = None


def get_retriever(top_k: int = 3, threshold: float = 0.7) -> Retriever:
    """获取或创建全局检索器。"""
    global _retriever
    _retriever = Retriever(top_k=top_k, threshold=threshold)
    return _retriever
