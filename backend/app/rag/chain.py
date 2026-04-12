"""RAG chain for retrieval-augmented generation."""

import logging
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.wrappers.llm import get_llm

logger = logging.getLogger(__name__)


class RAGChain:
    """RAG chain for answering questions with knowledge base context."""

    def __init__(
        self,
        top_k: int = 3,
        threshold: float = 0.7,
    ):
        """Initialize RAG chain.

        Args:
            top_k: Number of chunks to retrieve
            threshold: Minimum similarity score
        """
        from app.rag.retriever import get_retriever

        self.retriever = get_retriever(top_k=top_k, threshold=threshold)
        self.llm = get_llm()

    async def query(
        self,
        question: str,
        filter_tokens: Optional[list[str]] = None,
    ) -> dict:
        """Query with RAG context.

        Args:
            question: User question
            filter_tokens: Optional token symbols to filter by

        Returns:
            Dict with answer and sources
        """
        # Retrieve relevant chunks
        chunks = await self.retriever.search(
            query=question,
            filter_tokens=filter_tokens,
        )

        if not chunks:
            return {
                "answer": "No relevant information found in the knowledge base.",
                "sources": [],
            }

        # Build context from chunks
        context_parts = []
        sources = []

        for i, chunk in enumerate(chunks):
            context_parts.append(f"[Source {i+1}] {chunk['content']}")
            sources.append({
                "chunk_id": chunk["chunk_id"],
                "similarity": chunk["similarity"],
            })

        context = "\n\n".join(context_parts)

        # Generate answer with context
        prompt = f"""Based on the following context from our knowledge base, answer the question.

Context:
{context}

Question: {question}

Provide a concise answer. If the context doesn't contain relevant information, say so."""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            answer = response.content.strip() if hasattr(response, "content") else str(response)

            return {
                "answer": answer,
                "sources": sources,
                "context_chunks": len(chunks),
            }
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return {
                "answer": f"Error generating answer: {str(e)}",
                "sources": sources,
            }

    async def enhance_token_context(
        self,
        token: str,
        news_content: str,
    ) -> dict:
        """Enhance token analysis with knowledge base information.

        Args:
            token: Token symbol
            news_content: News content to analyze with

        Returns:
            Enhanced context with KB information
        """
        # Search for token-related chunks
        chunks = await self.retriever.search(
            query=f"Information about {token} cryptocurrency",
            filter_tokens=[token],
        )

        if not chunks:
            return {
                "token": token,
                "kb_found": False,
                "enhanced_context": None,
            }

        # Build enhanced context
        kb_info = "\n\n".join([
            f"- {chunk['content'][:200]}..."
            for chunk in chunks[:3]
        ])

        # Analyze news with KB context
        prompt = f"""You are analyzing news about cryptocurrency {token}.

Knowledge Base Information:
{kb_info}

Recent News:
{news_content}

Based on the knowledge base, provide:
1. Key facts about {token}
2. How the news relates to these facts
3. Any important context for investors"""

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
            logger.error(f"Error enhancing token context: {e}")
            return {
                "token": token,
                "kb_found": True,
                "kb_chunks": len(chunks),
                "analysis": f"Error: {str(e)}",
            }


# Global RAG chain instance
_chain: Optional[RAGChain] = None


def get_rag_chain(top_k: int = 3, threshold: float = 0.7) -> RAGChain:
    """Get or create global RAG chain."""
    global _chain
    _chain = RAGChain(top_k=top_k, threshold=threshold)
    return _chain
