"""CoinMarketCap API client.

Fetches token market data including price, market cap, and 24h change.
"""

import logging
from typing import Any

import httpx

from app.core.config import cfg

logger = logging.getLogger(__name__)


class CMCClient:
    """Client for CoinMarketCap API.

    Provides token market data lookup functionality.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://pro-api.coinmarketcap.com",
    ):
        """Initialize CMC client.

        Args:
            api_key: CMC API key (defaults to cfg.cmc.CMC_API_KEY)
            base_url: CMC API base URL
        """
        self.api_key = api_key or cfg.cmc.CMC_API_KEY
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
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
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_token_info(self, symbol: str) -> dict[str, Any] | None:
        """Get token market information by symbol.

        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")

        Returns:
            Dictionary with keys: symbol, name, price, market_cap, change_24h
            Returns None if token not found or API error
        """
        try:
            client = await self._get_client()

            # Try v2 /quotes/latest API
            params = {"symbol": symbol.upper()}
            response = await client.get("/v2/cryptocurrency/quotes/latest", params=params)

            if response.status_code == 429:
                logger.warning(f"CMC rate limited for {symbol}")
                return None

            if response.status_code != 200:
                logger.warning(f"CMC error {response.status_code} for {symbol}")
                return None

            data = response.json()

            # Parse response - CMC v2 returns data as an array
            symbol_upper = symbol.upper()
            if (
                "data" in data
                and symbol_upper in data["data"]
            ):
                # CMC v2 API returns data as an array
                token_list = data["data"][symbol_upper]
                if isinstance(token_list, list) and len(token_list) > 0:
                    token_data = token_list[0]  # Take the first result
                else:
                    token_data = token_list  # Fallback for single object

                quote = token_data.get("quote", {}).get("USD", {})

                return {
                    "symbol": token_data["symbol"],
                    "name": token_data["name"],
                    "price": quote.get("price"),
                    "market_cap": quote.get("market_cap"),
                    "change_24h": quote.get("percent_change_24h"),
                    "volume_24h": quote.get("volume_24h"),
                }

            logger.info(f"Token {symbol} not found in CMC")
            return None

        except Exception as e:
            logger.error(f"Error fetching CMC data for {symbol}: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if CMC API is accessible."""
        try:
            result = await self.get_token_info("BTC")
            return result is not None
        except Exception:
            return False
