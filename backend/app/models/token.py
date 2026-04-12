"""Token model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db import Base


class Token(Base):
    """Cryptocurrency token information."""

    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_price: Mapped[Optional[Numeric]] = mapped_column(Numeric(20, 8), nullable=True)
    market_cap: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    volume_24h: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    change_24h_percent: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 2), nullable=True)

    # Additional metadata
    cmc_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # CoinMarketCap ID
    coingecko_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contract_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Token(symbol={self.symbol}, name={self.name})>"
