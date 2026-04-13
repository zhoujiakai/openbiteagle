"""RAG 知识库文档模型。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.data.db import Base


class Document(Base):
    """知识库文档。"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="自增主键"
    )
    title: Mapped[str] = mapped_column(
        String(500), comment="文档标题"
    )
    content: Mapped[str] = mapped_column(
        Text, comment="文档正文内容"
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True, comment="来源 URL"
    )
    source_type: Mapped[str] = mapped_column(
        String(50), default="manual", comment="来源类型：manual/rootdata/odaily"
    )
    meta_data: Mapped[dict] = mapped_column(
        JSON, default=dict, comment="附加元数据（JSON）"
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False, comment="记录创建时间"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title[:30]}...')>"


class DocumentChunk(Base):
    """文档分块，包含向量嵌入，用于相似度检索。"""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="自增主键"
    )
    document_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="所属文档 ID"
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="分块在文档中的序号"
    )

    content: Mapped[str] = mapped_column(
        Text, comment="分块文本内容"
    )
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1024), nullable=True, comment="向量嵌入（1024 维）"
    )
    meta_data: Mapped[dict] = mapped_column(
        JSON, default=dict, comment="附加元数据（JSON）"
    )

    # 当前分块中提及的代币
    tokens: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, comment="当前分块中提及的代币符号列表"
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False, comment="记录创建时间"
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"
