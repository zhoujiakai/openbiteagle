"""新闻模型。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db import Base


class News(Base):
    """Odaily 快讯/文章。"""

    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    source_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, comment="Odaily 快讯 ID")
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True, comment="标题")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="正文（HTML 格式）")
    images: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, comment="图片 URL 列表")
    isImportant: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否重要快讯")
    publishTimestamp: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="发布时间戳（ms）")
    publishDate: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="发布时间，格式 yyyy-MM-dd HH:mm:ss")
    sourceUrl: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True, comment="原文外链")
    link: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True, comment="Odaily 站内详情页 URL")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="记录创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="记录更新时间"
    )

    def __repr__(self) -> str:
        return f"<News(id={self.id}, title={self.title[:30]}...)>"
