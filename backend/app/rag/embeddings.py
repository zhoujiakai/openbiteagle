"""文本向量化嵌入服务。"""

from typing import Optional

import httpx
from pydantic import BaseModel, Field

from app.core.config import cfg
from app.data.logger import create_logger

logger = create_logger("文本向量化")


# ── LLM 代币提取 ──────────────────────────────────────────────

class TokenSymbolOutput(BaseModel):
    """LLM 结构化输出：代币符号列表。"""
    symbols: list[str] = Field(default_factory=list, description="提取到的代币符号列表，如 ['BTC', 'ETH']")


_TOKEN_EXTRACTION_PROMPT = """你是一名加密货币专家。请从以下文本中提取所有相关的加密货币代币符号。

## 文本内容
{content}

## 任务

识别文本中提到的加密货币、区块链项目或公司，返回它们的交易代码（symbol），例如 BTC、ETH、SOL 等。

要求：
- 能识别中文描述（如"比特币"→BTC、"以太坊"→ETH、"索拉纳"→SOL）
- 能识别英文全称（如 Bitcoin→BTC、Ethereum→ETH）
- 能识别常见变体写法和简称
- 能识别项目/公司关联的代币（如提到 Circle 应返回 USDC，提到 Uniswap 应返回 UNI）
- 排除已停止维护/废弃的项目
- 排除仅被一带而过、与主题无关的代币
- 宁可多提取也不要遗漏，因为结果用于 RAG 检索过滤

如果未找到相关代币，请返回空列表。"""


async def extract_tokens_from_text(text: str) -> list[str]:
    """调用 LLM 从文本中提取代币符号。

    Args:
        text: 待提取的文本（建议不超过 2000 字符以提高速度和准确性）

    Returns:
        代币符号列表，如 ["BTC", "ETH"]
    """
    from app.wrappers.llm.client import call_llm_structured, get_llm

    llm = get_llm(temperature=0)
    prompt = _TOKEN_EXTRACTION_PROMPT.format(content=text[:2000])

    schema = {
        "type": "object",
        "properties": {
            "symbols": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": ["symbols"],
    }

    try:
        result = await call_llm_structured(llm, prompt, TokenSymbolOutput, schema)
        tokens = [s.upper() for s in result.symbols]
        logger.info(f"LLM 提取代币: {tokens}")
        return tokens
    except Exception as e:
        logger.warning(f"LLM 代币提取失败: {e}")
        return []


# ── 嵌入服务 ──────────────────────────────────────────────────


class JinaEmbeddings:
    """基于 HTTP API 的 Jina Embeddings 客户端。"""

    def __init__(self, model: str = None, api_key: str = None):
        self.model = model or cfg.jina.JINA_EMBEDDING_MODEL
        self.api_key = api_key or cfg.jina.JINA_API_KEY
        self.api_url = cfg.jina.JINA_API_URL
        self.timeout = cfg.jina.JINA_TIMEOUT
        self.batch_size = cfg.jina.JINA_BATCH_SIZE
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def aembed_query(self, text: str) -> list[float]:
        """为单条文本生成嵌入向量。"""
        response = await self.client.post(
            self.api_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            json={
                "model": self.model,
                "input": [text],
                "encoding_format": "float",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """为多条文本批量生成嵌入向量。"""
        # 按 Jina 批量大小分批请求
        all_embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            response = await self.client.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model,
                    "input": batch,
                    "encoding_format": "float",
                },
            )
            response.raise_for_status()
            data = response.json()
            batch_embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def close(self):
        """关闭 HTTP 客户端。"""
        if self._client:
            await self._client.aclose()


class EmbeddingService:
    """嵌入向量生成与存储服务。"""

    def __init__(self, model: str = None):
        """初始化嵌入服务。

        Args:
            model: Jina 嵌入模型名称（默认从配置读取）
        """
        self._embeddings: Optional[JinaEmbeddings] = None
        self.model = model or cfg.jina.JINA_EMBEDDING_MODEL

    @property
    def embeddings(self) -> JinaEmbeddings:
        """获取或创建嵌入实例。"""
        if self._embeddings is None:
            logger.info(f"使用 Jina 嵌入模型: {self.model}")
            self._embeddings = JinaEmbeddings(
                model=self.model,
                api_key=cfg.jina.JINA_API_KEY,
            )
        return self._embeddings

    async def close(self):
        """关闭嵌入服务。"""
        if self._embeddings:
            await self._embeddings.close()

    async def embed_text(self, text: str) -> list[float]:
        """为单条文本生成嵌入向量。

        Args:
            text: 待嵌入的文本

        Returns:
            嵌入向量
        """
        result = await self.embeddings.aembed_query(text)
        return result

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """为多条文本生成嵌入向量。

        Args:
            texts: 待嵌入的文本列表

        Returns:
            嵌入向量列表
        """
        results = await self.embeddings.aembed_documents(texts)
        return results

    def _split_text(self, text: str, chunk_size: int = None, chunk_overlap: int = None) -> list[str]:
        """将文本按指定大小分块，支持重叠。

        Args:
            text: 待分割的文本
            chunk_size: 目标分块大小（字符数）
            chunk_overlap: 相邻分块的重叠字符数

        Returns:
            文本分块列表
        """
        chunk_size = chunk_size or cfg.jina.CHUNK_SIZE
        chunk_overlap = chunk_overlap or cfg.jina.CHUNK_OVERLAP

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            # 尝试在句子边界处断开
            if end < len(text):
                for sep in [". ", "! ", "? ", "\n\n", "\n"]:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep != -1:
                        end = last_sep + len(sep)
                        break

            chunks.append(text[start:end].strip())
            new_start = end - chunk_overlap
            if new_start <= start:
                start = end
            else:
                start = new_start

        return [c for c in chunks if c]

    async def process_document(
        self,
        document_id: int,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ) -> dict:
        """将文档分块并生成嵌入向量。

        Args:
            document_id: 待处理的文档 ID
            chunk_size: 每个分块的字符数
            chunk_overlap: 相邻分块的重叠字符数

        Returns:
            包含处理统计信息的字典
        """
        from app.data.db import AsyncSessionLocal
        from app.data.vector import get_document
        from app.models.document import DocumentChunk
        from pgvector.sqlalchemy import Vector

        doc = await get_document(document_id)
        if not doc:
            raise ValueError(f"文档 {document_id} 不存在")

        chunks = self._split_text(doc.content, chunk_size, chunk_overlap)
        logger.info(f"文档 {document_id} 已分割为 {len(chunks)} 个分块")

        embedding_vectors = await self.embed_texts(chunks)

        # 从文档 metadata 中提取 tokens
        doc_tokens = (doc.meta_data or {}).get("tokens", [])

        # 如果文档 metadata 没有 tokens，调用 LLM 从标题和内容中提取
        if not doc_tokens:
            doc_tokens = await extract_tokens_from_text(
                f"{doc.title} {doc.content[:2000]}"
            )

        async with AsyncSessionLocal() as db:
            for i, (chunk, embedding) in enumerate(zip(chunks, embedding_vectors)):
                # 每个 chunk 继承文档级 tokens
                chunk_record = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk,
                    embedding=embedding,
                    tokens=list(doc_tokens),
                )
                db.add(chunk_record)

            await db.commit()

        return {
            "document_id": document_id,
            "chunks_created": len(chunks),
            "embedding_dim": len(embedding_vectors[0]) if embedding_vectors else 0,
        }


# 全局嵌入服务实例
_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取或创建全局嵌入服务。"""
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service
