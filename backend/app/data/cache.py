"""Redis cache client.

Reference: repos/back-template/data/cache.py
"""

import logging
from typing import Any, Optional

import redis.asyncio as aioredis
from pydantic import BaseModel

from app.core.config import cfg

logger = logging.getLogger(__name__)

# 所有键的前缀
PREFIX = "biteagle:"


class Cache:
    """Redis cache client."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._client is None:
            self._client = aioredis.from_url(cfg.redis.REDIS_URL)
        return self._client

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        client = await self.connect()
        await client.delete(str(key))

    async def get(
        self,
        key: str,
        model: Optional[type] = None,
    ) -> Any:
        """Get value from cache.

        Args:
            key: Cache key
            model: Optional pydantic model for deserialization

        Returns:
            Cached value or None
        """
        client = await self.connect()
        data = await client.get(str(key))
        if data is None:
            return None
        if model is None or model is bytes:
            return data
        if model is str:
            return data.decode()
        if issubclass(model, BaseModel):
            return model.model_validate_json(data)
        import json
        return json.loads(data)

    async def set(
        self,
        key: str,
        value: Any,
        *,
        expire: Optional[int] = None,
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds
        """
        import json

        client = await self.connect()
        if isinstance(value, (str, bytes)):
            data = value
        elif isinstance(value, BaseModel):
            data = value.model_dump_json()
        else:
            data = json.dumps(value)

        if expire:
            await client.setex(str(key), expire, data)
        else:
            await client.set(str(key), data)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        client = await self.connect()
        return await client.exists(str(key)) > 0

    async def incr(self, key: str) -> int:
        """Increment value."""
        client = await self.connect()
        return await client.incr(str(key))


# 全局缓存实例
_cache: Optional[Cache] = None


async def get_cache() -> Cache:
    """Get or create global cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


async def close_cache() -> None:
    """Close global cache instance."""
    global _cache
    if _cache:
        await _cache.close()
        _cache = None
