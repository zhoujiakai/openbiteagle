"""Data layer - database, cache, and message queue."""

from aio_pika import RobustChannel, RobustConnection
from aio_pika.abc import AbstractIncomingMessage

from app.data.cache import Cache, close_cache, get_cache
from app.data.db import AsyncSession, AsyncSessionLocal, Base, engine, get_db
from app.data.rabbit import RabbitMQ, close_rabbit, get_rabbit

# Type alias for convenience
IncomingMessage = AbstractIncomingMessage

__all__ = [
    # Database
    "AsyncSession",
    "AsyncSessionLocal",
    "Base",
    "engine",
    "get_db",
    # Cache
    "Cache",
    "get_cache",
    "close_cache",
    # RabbitMQ
    "RabbitMQ",
    "get_rabbit",
    "close_rabbit",
    "IncomingMessage",
    "RobustChannel",
    "RobustConnection",
]
