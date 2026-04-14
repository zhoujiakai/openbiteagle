"""GeckoTerminal API client (backup/fallback for CMC).

GeckoTerminal provides free DEX data without API key requirements.
Can be used as fallback when CMC is unavailable.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GeckoClient:
    """Client for GeckoTerminal API.

    Provides token market data from decentralized exchanges.
    Free to use, no API key required.
    """

    def __init__(self, base_url: str = "https://api.geckoterminal.com/api/v2"):
        """Initialize GeckoTerminal client.

        Args:
            base_url: GeckoTerminal API base URL
        """
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_token(self, query: str) -> list[dict[str, Any]]:
        """Search for tokens by name or symbol.

        Args:
            query: Token name or symbol (e.g., "bitcoin", "BTC")

        Returns:
            List of matching tokens with basic info
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
        """Get token price from DEX pools.

        Args:
            token_address: Token contract address
            network: Network identifier (eth, sol, base, etc.)

        Returns:
            Dictionary with price info or None
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
        """Check if GeckoTerminal API is accessible."""
        try:
            client = await self._get_client()
            response = await client.get("/networks")
            return response.status_code == 200
        except Exception:
            return False
