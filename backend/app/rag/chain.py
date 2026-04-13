"""RAG 检索增强生成链。"""

import logging
from typing import Optional

from langchain_core.messages import HumanMessage

from app.wrappers.llm import get_llm

logger = logging.getLogger(__name__)


class RAGChain:
    """基于知识库上下文回答问题的 RAG 链。"""

    def __init__(
        self,
        top_k: int = 3,
        threshold: float = 0.7,
    ):
        """初始化 RAG 链。

        Args:
            top_k: 检索的分块数量
            threshold: 最低相似度阈值
        """
        from app.rag.retriever import get_retriever

        self.retriever = get_retriever(top_k=top_k, threshold=threshold)
        self.llm = get_llm()

    async def query(
        self,
        question: str,
        filter_tokens: Optional[list[str]] = None,
    ) -> dict:
        """基于 RAG 上下文进行查询。

        Args:
            question: 用户问题
            filter_tokens: 可选的代币符号过滤列表

        Returns:
            包含答案和来源的字典
        """
        # 检索相关分块
        chunks = await self.retriever.search(
            query=question,
            filter_tokens=filter_tokens,
        )

        if not chunks:
            return {
                "answer": "在知识库中未找到相关信息。",
                "sources": [],
            }

        # 从分块构建上下文
        context_parts = []
        sources = []

        for i, chunk in enumerate(chunks):
            context_parts.append(f"[来源 {i+1}] {chunk['content']}")
            sources.append({
                "chunk_id": chunk["chunk_id"],
                "similarity": chunk["similarity"],
            })

        context = "\n\n".join(context_parts)

        # 基于上下文生成回答
        prompt = f"""请根据以下知识库上下文回答问题。

上下文：
{context}

问题：{question}

请提供简洁的回答。如果上下文中不包含相关信息，请如实说明。"""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            answer = response.content.strip() if hasattr(response, "content") else str(response)

            return {
                "answer": answer,
                "sources": sources,
                "context_chunks": len(chunks),
            }
        except Exception as e:
            logger.error(f"RAG 查询出错: {e}")
            return {
                "answer": f"生成回答时出错: {str(e)}",
                "sources": sources,
            }

    async def enhance_token_context(
        self,
        token: str,
        news_content: str,
    ) -> dict:
        """利用知识库信息增强代币分析。

        Args:
            token: 代币符号
            news_content: 待分析的新闻内容

        Returns:
            包含知识库增强上下文的字典
        """
        # 搜索与代币相关的分块
        chunks = await self.retriever.search(
            query=f"关于 {token} 加密货币的信息",
            filter_tokens=[token],
        )

        if not chunks:
            return {
                "token": token,
                "kb_found": False,
                "enhanced_context": None,
            }

        # 构建增强上下文
        kb_info = "\n\n".join([
            f"- {chunk['content'][:200]}..."
            for chunk in chunks[:3]
        ])

        # 基于知识库上下文分析新闻
        prompt = f"""你正在分析关于加密货币 {token} 的新闻。

知识库信息：
{kb_info}

最新新闻：
{news_content}

请根据知识库提供：
1. 关于 {token} 的关键信息
2. 新闻与这些信息的关联
3. 对投资者重要的背景信息"""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            analysis = response.content.strip() if hasattr(response, "content") else str(response)

            return {
                "token": token,
                "kb_found": True,
                "kb_chunks": len(chunks),
                "analysis": analysis,
            }
        except Exception as e:
            logger.error(f"增强代币上下文出错: {e}")
            return {
                "token": token,
                "kb_found": True,
                "kb_chunks": len(chunks),
                "analysis": f"出错: {str(e)}",
            }


# 全局 RAG 链实例
_chain: Optional[RAGChain] = None


def get_rag_chain(top_k: int = 3, threshold: float = 0.7) -> RAGChain:
    """获取或创建全局 RAG 链。"""
    global _chain
    _chain = RAGChain(top_k=top_k, threshold=threshold)
    return _chain
