"""RabbitMQ 客户端。

参考: repos/back-template/data/rabbit.py
"""

import asyncio
from typing import Any, AsyncGenerator, Optional, Tuple

import aio_pika
from aio_pika import RobustConnection, RobustChannel, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractIncomingMessage,
)
import json

from app.core.config import cfg
from data import create_logger

logger = create_logger("消息队列")

__all__ = [
    "RabbitMQ",
    "IncomingMessage",
    "RobustConnection",
    "RobustChannel",
]


class RabbitMQ:
    """带自动重连的异步 RabbitMQ 客户端。"""

    def __init__(self) -> None:
        """初始化 RabbitMQ 客户端。"""
        self._connection: Optional[RobustConnection] = None
        self._channel: Optional[RobustChannel] = None
        self._exchange: Optional[AbstractExchange] = None
        self._exchange_name = "biteagle"
        self._ready = asyncio.Event()
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _initialize(self) -> None:
        """初始化到 RabbitMQ 的连接。"""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            self._connection = await aio_pika.connect_robust(cfg.rabbitmq.RABBITMQ_URL)
            self._channel = await self._connection.channel()

            # 声明交换机
            self._exchange = await self._channel.declare_exchange(
                self._exchange_name,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )

            # 声明队列
            self._main_queue = await self._channel.declare_queue(
                cfg.rabbitmq.RABBITMQ_QUEUE,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": self._exchange_name,
                    "x-dead-letter-routing-key": cfg.rabbitmq.RABBITMQ_DLQ,
                },
            )

            self._dlq_queue = await self._channel.declare_queue(
                cfg.rabbitmq.RABBITMQ_DLQ,
                durable=True,
            )

            # 绑定队列
            await self._main_queue.bind(self._exchange, cfg.rabbitmq.RABBITMQ_QUEUE)
            await self._dlq_queue.bind(self._exchange, cfg.rabbitmq.RABBITMQ_DLQ)

            self._initialized = True
            self._ready.set()

    async def _get_channel(self) -> AbstractChannel:
        """获取通道。"""
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
        """向指定队列发送消息。

        Args:
            queue: 队列名称
            message: 消息内容（可以是 dict、str、bytes）
            **kwargs: 附加选项（delivery_mode 等）
        """
        from pydantic import BaseModel

        channel = await self._get_channel()

        # 序列化消息
        if isinstance(message, BaseModel):
            data = message.model_dump_json().encode()
        elif isinstance(message, str):
            data = message.encode()
        elif isinstance(message, bytes):
            data = message
        else:
            data = json.dumps(message).encode()

        # 获取投递模式
        delivery_mode = kwargs.pop("delivery_mode", None)
        if delivery_mode is not None:
            try:
                delivery_mode = int(delivery_mode)
            except:
                delivery_mode = None

        # 发布消息
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
        """从指定队列接收消息。

        Args:
            queue_name: 队列名称

        Yields:
            (消息体, 收到的消息) 元组
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
        """关闭 RabbitMQ 连接。"""
        if self._connection is not None:
            await self._connection.close()


# 全局 RabbitMQ 实例
_rabbit: Optional[RabbitMQ] = None


async def get_rabbit() -> RabbitMQ:
    """获取或创建全局 RabbitMQ 实例。"""
    global _rabbit
    if _rabbit is None:
        _rabbit = RabbitMQ()
    return _rabbit


async def close_rabbit() -> None:
    """关闭全局 RabbitMQ 实例。"""
    global _rabbit
    if _rabbit:
        await _rabbit.close()
        _rabbit = None
