"""RabbitMQ client.

Reference: repos/back-template/data/rabbit.py
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Optional, Tuple

import aio_pika
from aio_pika import RobustConnection, RobustChannel, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractQueue,
)
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

__all__ = [
    "RabbitMQ",
    "IncomingMessage",
    "RobustConnection",
    "RobustChannel",
]


class RabbitMQ:
    """Asynchronous RabbitMQ client with auto-reconnect."""

    def __init__(self) -> None:
        """Initialize RabbitMQ client."""
        self._connection: Optional[RobustConnection] = None
        self._channel: Optional[RobustChannel] = None
        self._exchange: Optional[AbstractExchange] = None
        self._exchange_name = "biteagle"
        self._ready = asyncio.Event()
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _initialize(self) -> None:
        """Initialize connection to RabbitMQ."""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self._channel = await self._connection.channel()

            # Declare exchange
            self._exchange = await self._channel.declare_exchange(
                self._exchange_name,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )

            # Declare queues
            self._main_queue = await self._channel.declare_queue(
                settings.RABBITMQ_QUEUE,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": self._exchange_name,
                    "x-dead-letter-routing-key": settings.RABBITMQ_DLQ,
                },
            )

            self._dlq_queue = await self._channel.declare_queue(
                settings.RABBITMQ_DLQ,
                durable=True,
            )

            # Bind queues
            await self._main_queue.bind(self._exchange, settings.RABBITMQ_QUEUE)
            await self._dlq_queue.bind(self._exchange, settings.RABBITMQ_DLQ)

            self._initialized = True
            self._ready.set()

    async def _get_channel(self) -> AbstractChannel:
        """Get the channel."""
        if not self._initialized:
            await self._initialize()
        await self._ready.wait()
        assert self._channel is not None
        return self._channel

    async def send(
        self,
        queue: str,
        message: Any,
        **kwargs,
    ) -> None:
        """Send a message to the specified queue.

        Args:
            queue: Queue name
            message: Message content (can be dict, str, bytes)
            **kwargs: Additional options (delivery_mode, etc.)
        """
        from pydantic import BaseModel

        channel = await self._get_channel()

        # Serialize message
        if isinstance(message, BaseModel):
            data = message.model_dump_json().encode()
        elif isinstance(message, str):
            data = message.encode()
        elif isinstance(message, bytes):
            data = message
        else:
            data = json.dumps(message).encode()

        # Get delivery mode
        delivery_mode = kwargs.pop("delivery_mode", None)
        if delivery_mode is not None:
            try:
                delivery_mode = int(delivery_mode)
            except:
                delivery_mode = None

        # Publish message
        await self._exchange.publish(
            Message(
                body=data,
                content_type="application/json",
                content_encoding="utf-8",
                delivery_mode=delivery_mode,
                **kwargs,
            ),
            queue,
        )

    def receive(
        self,
        queue_name: str,
    ) -> AsyncGenerator[Tuple[bytes, AbstractIncomingMessage], None]:
        """Receive messages from the specified queue.

        Args:
            queue_name: Queue name

        Yields:
            Tuple of (message body, incoming message)
        """
        async def _receive():
            await self._initialize()
            assert self._connection is not None

            while True:
                try:
                    async with self._connection.channel() as channel:
                        queue = await channel.get_queue(queue_name, ensure=True)

                        async with queue.iterator() as queue_iter:
                            async for message in queue_iter:
                                yield message.body, message

                except Exception as e:
                    logger.error(f"RabbitMQ connection error: {e}")
                    await asyncio.sleep(5)
                    continue

        return _receive()

    async def close(self) -> None:
        """Close the RabbitMQ connection."""
        if self._connection is not None:
            await self._connection.close()


# Global RabbitMQ instance
_rabbit: Optional[RabbitMQ] = None


async def get_rabbit() -> RabbitMQ:
    """Get or create global RabbitMQ instance."""
    global _rabbit
    if _rabbit is None:
        _rabbit = RabbitMQ()
    return _rabbit


async def close_rabbit() -> None:
    """Close global RabbitMQ instance."""
    global _rabbit
    if _rabbit:
        await _rabbit.close()
        _rabbit = None
