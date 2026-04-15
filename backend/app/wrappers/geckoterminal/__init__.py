"""GeckoTerminal API 客户端（CMC 的备用方案）。

GeckoTerminal 提供免费的 DEX 数据，无需 API 密钥。
可在 CMC 不可用时作为备用。
"""

from typing import Any

import httpx

from app.data.logger import create_logger

logger = create_logger("GeckoTerminal")


class GeckoClient:
    """GeckoTerminal API 客户端。

    提供来自去中心化交易所的代币市场数据。
    免费使用，无需 API 密钥。
    """

    def __init__(self, base_url: str = "https://api.geckoterminal.com/api/v2"):
        """初始化 GeckoTerminal 客户端。

        Args:
            base_url: GeckoTerminal API 基础 URL
        """
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端。"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
        return self._client

    async def close(self):
        """关闭 HTTP 客户端。"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_token(self, query: str) -> list[dict[str, Any]]:
        """按名称或符号搜索代币。

        Args:
            query: 代币名称或符号（例如 "bitcoin"、"BTC"）

        Returns:
            匹配的代币列表（包含基本信息）
        """
        try:
            client = await self._get_client()

            params = {"query": query}
            response = await client.get("/search/pools", params=params)

            if response.status_code != 200:
                return []

            data = response.json()
            return data.get("data", [])

        except Exception as e:
            logger.error(f"Error searching GeckoTerminal for {query}: {e}")
            return []

    async def get_token_price(
        self, token_address: str, network: str = "eth"
    ) -> dict[str, Any] | None:
        """从 DEX 池获取代币价格。

        Args:
            token_address: 代币合约地址
            network: 网络标识（eth、sol、base 等）

        Returns:
            包含价格信息的字典或 None
        """
        try:
            client = await self._get_client()

            response = await client.get(
                f"/networks/{network}/tokens/{token_address}/pools"
            )

            if response.status_code != 200:
                return None

            data = response.json()
            pools = data.get("data", [])

            if not pools:
                return None

            # 获取流动性最高的池子数据
            top_pool = pools[0]["attributes"]
            return {
                "address": token_address,
                "price_usd": top_pool.get("base_token_price_usd"),
                "liquidity_usd": top_pool.get("reserve_in_usd"),
                "volume_24h_usd": top_pool.get("volume_usd", {}).get("h24"),
            }

        except Exception as e:
            logger.error(f"Error fetching GeckoTerminal price: {e}")
            return None

    async def health_check(self) -> bool:
        """检查 GeckoTerminal API 是否可访问。"""
        try:
            client = await self._get_client()
            response = await client.get("/networks")
            return response.status_code == 200
        except Exception:
            return False
