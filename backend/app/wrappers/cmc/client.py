"""CoinMarketCap API 客户端。

获取代币市场数据，包括价格、市值和 24 小时涨跌。
"""

import asyncio
from typing import Any

import httpx

from app.core.config import cfg
from app.data.logger import create_logger

logger = create_logger("CMC查询代币市场信息")


class CMCClient:
    """CoinMarketCap API 客户端。

    提供代币市场数据查询功能。
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://pro-api.coinmarketcap.com",
    ):
        """初始化 CMC 客户端。

        Args:
            api_key: CMC API 密钥（默认使用 cfg.cmc.CMC_API_KEY）
            base_url: CMC API 基础 URL
        """
        self.api_key = api_key or cfg.cmc.CMC_API_KEY
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端。"""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["X-CMC_PRO_API_KEY"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=10.0,
            )
        return self._client

    async def close(self):
        """关闭 HTTP 客户端。"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_token_info(
        self, symbol: str, *, retries: int = 3
    ) -> dict[str, Any] | None:
        """根据符号获取代币市场信息。

        Args:
            symbol: 代币符号（例如 "BTC"、"ETH"）
            retries: 请求失败时的重试次数，默认 3 次

        Returns:
            包含以下键的字典：symbol、name、price、market_cap、change_24h
            如果未找到代币或 API 错误（重试耗尽后）则返回 None
        """
        last_error: str | None = None

        for attempt in range(1, retries + 1):
            try:
                client = await self._get_client()

                # 尝试 v2 /quotes/latest API
                params = {"symbol": symbol.upper()}
                response = await client.get(
                    "/v2/cryptocurrency/quotes/latest", params=params
                )

                if response.status_code == 429:
                    last_error = f"CMC 请求限流: {symbol}"
                    logger.warning(
                        f"{last_error}（第 {attempt}/{retries} 次尝试）"
                    )
                    if attempt < retries:
                        await asyncio.sleep(1)
                    continue

                if response.status_code != 200:
                    last_error = (
                        f"CMC 请求错误 {response.status_code}: {symbol}"
                    )
                    logger.warning(
                        f"{last_error}（第 {attempt}/{retries} 次尝试）"
                    )
                    if attempt < retries:
                        await asyncio.sleep(1)
                    continue

                data = response.json()

                # 解析响应 - CMC v2 返回数据为数组
                symbol_upper = symbol.upper()
                if (
                    "data" in data
                    and symbol_upper in data["data"]
                ):
                    # CMC v2 API 返回数据为数组
                    token_list = data["data"][symbol_upper]
                    if isinstance(token_list, list) and len(token_list) > 0:
                        token_data = token_list[0]  # 取第一个结果
                    else:
                        token_data = token_list  # 单对象时直接使用

                    # quote(报价) 是 CMC 返回的价格行情数据, 按法币分类, 这里取 USD 报价
                    quote = token_data.get("quote", {}).get("USD", {})

                    return {
                        "symbol": token_data["symbol"],          # 代币符号, 如 BTC, ETH
                        "name": token_data["name"],              # 代币全称, 如 Bitcoin, Ethereum
                        "price": quote.get("price"),              # 当前价格 (USD)
                        "market_cap": quote.get("market_cap"),    # 市值 (USD)
                        "change_24h": quote.get("percent_change_24h"),  # 24小时涨跌幅 (%)
                        "volume_24h": quote.get("volume_24h"),    # 24小时交易量 (USD)
                    }

                logger.info(f"在 CMC 中未找到代币 {symbol}")
                return None

            except Exception as e:
                last_error = f"获取 {symbol} 的 CMC 数据失败: {e}"
                logger.error(f"{last_error}（第 {attempt}/{retries} 次尝试）")
                if attempt < retries:
                    await asyncio.sleep(1)
                continue

        logger.error(
            f"获取 {symbol} 的 CMC 数据在 {retries} 次重试后仍失败: {last_error}"
        )
        return None

    async def health_check(self) -> bool:
        """检查 CMC API 是否可访问。"""
        try:
            result = await self.get_token_info("BTC")
            return result is not None
        except Exception:
            return False
