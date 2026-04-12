"""Analysis model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db import Base


class Analysis(Base):
    """Investment analysis result for a news item."""

    __tablename__ = "analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )  # pending/processing/completed/failed

    # Investment value judgment
    investment_value: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # bullish/bearish/neutral
    confidence: Mapped[Optional[Numeric]] = mapped_column(Numeric(3, 2), nullable=True)

    # Token information
    tokens: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Analysis results
    trend_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # buy/sell/hold

    # Analysis steps (each node's result)
    steps: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Execution tracking
    langsmith_trace: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, news_id={self.news_id}, status={self.status})>"
