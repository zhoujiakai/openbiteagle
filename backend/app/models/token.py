"""代币模型。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.data.db import Base


class Token(Base):
    """加密货币代币信息。"""

    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="自增主键"
    )
    symbol: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True, comment="代币符号，如 BTC、ETH"
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="代币全称"
    )
    current_price: Mapped[Optional[Numeric]] = mapped_column(
        Numeric(20, 8), nullable=True, comment="当前价格（USD）"
    )
    market_cap: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="市值（USD）"
    )
    volume_24h: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="24 小时交易量（USD）"
    )
    change_24h_percent: Mapped[Optional[Numeric]] = mapped_column(
        Numeric(10, 2), nullable=True, comment="24 小时价格涨跌幅百分比"
    )

    # 附加元数据
    cmc_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="CoinMarketCap ID"
    )
    coingecko_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="CoinGecko ID"
    )
    contract_address: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="智能合约地址"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        comment="记录更新时间"
    )

    def __repr__(self) -> str:
        return f"<Token(symbol={self.symbol}, name={self.name})>"
