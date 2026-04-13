"""分析模型。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db import Base


class Analysis(Base):
    """新闻投资分析结果。"""

    __tablename__ = "analysis"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    news_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True, comment="关联的新闻 ID"
    )

    # 处理状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True,
        comment="处理状态：pending/processing/completed/failed"
    )

    # 投资价值判断
    investment_value: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="投资价值判断：bullish/bearish/neutral"
    )
    confidence: Mapped[Optional[Numeric]] = mapped_column(
        Numeric(3, 2), nullable=True, comment="置信度（0.00 ~ 1.00）"
    )

    # 代币信息
    tokens: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="相关代币信息（JSON）"
    )

    # 分析结果
    trend_analysis: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="趋势分析文本"
    )
    recommendation: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="推荐操作：buy/sell/hold"
    )

    # 分析步骤（每个节点的结果）
    steps: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="各分析节点的中间结果（JSON）"
    )

    # 执行追踪
    langsmith_trace: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="LangSmith 追踪 ID"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="错误信息"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="重试次数"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="记录创建时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="分析完成时间"
    )

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, news_id={self.news_id}, status={self.status})>"
