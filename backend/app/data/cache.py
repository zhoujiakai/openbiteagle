"""Redis 缓存客户端。

参考: repos/back-template/data/cache.py
"""

from typing import Any, Optional

import redis.asyncio as aioredis
from pydantic import BaseModel

from app.core.config import cfg
from app.data.logger import create_logger

logger = create_logger("Redis缓存")

# 所有键的前缀
PREFIX = "biteagle:"


class Cache:
    """Redis 缓存客户端。"""

    def __init__(self) -> None:
        """初始化 Redis 客户端。"""
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> aioredis.Redis:
        """获取或创建 Redis 连接。"""
        if self._client is None:
            self._client = aioredis.from_url(cfg.redis.REDIS_URL)
        return self._client

    async def close(self) -> None:
        """关闭 Redis 连接。"""
        if self._client:
            await self._client.close()
            self._client = None

    async def delete(self, key: str) -> None:
        """从缓存中删除键。"""
        client = await self.connect()
        await client.delete(str(key))

    async def get(
        self,
        key: str,
        model: Optional[type] = None,
    ) -> Any:
        """从缓存获取值。

        Args:
            key: 缓存键
            model: 可选的 Pydantic 模型，用于反序列化

        Returns:
            缓存的值或 None
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
        """在缓存中设置值。

        Args:
            key: 缓存键
            value: 要缓存的值
            expire: 过期时间（秒）
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
        """检查键是否存在。"""
        client = await self.connect()
        return await client.exists(str(key)) > 0

    async def incr(self, key: str) -> int:
        """递增值。"""
        client = await self.connect()
        return await client.incr(str(key))


# 全局缓存实例
_cache: Optional[Cache] = None


async def get_cache() -> Cache:
    """获取或创建全局缓存实例。"""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


async def close_cache() -> None:
    """关闭全局缓存实例。"""
    global _cache
    if _cache:
        await _cache.close()
        _cache = None
