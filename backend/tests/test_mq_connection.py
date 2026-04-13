#!/usr/bin/env python3
"""快速测试 RabbitMQ 和 Redis 连接。"""

import asyncio
import sys

import aio_pika
import redis.asyncio as aioredis


async def test_rabbitmq():
    """测试 RabbitMQ 连接。"""
    print("=" * 60)
    print("测试 RabbitMQ 连接")
    print("=" * 60)
    print("URL: amqp://admin:admin@localhost:5672")
    print()

    try:
        connection = await aio_pika.connect_robust(
            "amqp://admin:admin@localhost:5672",
            reconnect_interval=5,
        )

        # 创建通道
        channel = await connection.channel()

        # 声明交换机
        exchange = await channel.declare_exchange(
            "biteagle",
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )

        # 声明队列
        main_queue = await channel.declare_queue(
            "biteagle_analysis",
            durable=True,
            arguments={
                "x-dead-letter-exchange": "biteagle",
                "x-dead-letter-routing-key": "biteagle_analysis_dlq",
            },
        )

        dlq_queue = await channel.declare_queue(
            "biteagle_analysis_dlq",
            durable=True,
        )

        # 绑定队列
        await main_queue.bind(exchange, "biteagle_analysis")
        await dlq_queue.bind(exchange, "biteagle_analysis_dlq")

        print(f"✅ RabbitMQ 连接成功")
        print(f"   交换机: {exchange.name}")
        print(f"   主队列: {main_queue.name}")
        print(f"   死信队列: {dlq_queue.name}")

        await connection.close()
        return True

    except Exception as e:
        print(f"❌ RabbitMQ 连接失败: {e}")
        return False


async def test_redis():
    """测试 Redis 连接。"""
    print()
    print("=" * 60)
    print("测试 Redis 连接")
    print("=" * 60)
    print("URL: redis://localhost:6380")
    print()

    try:
        client = aioredis.from_url("redis://localhost:6380")
        await client.ping()
        print("✅ Redis 连接成功")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False


async def test_producer():
    """测试发送消息。"""
    print()
    print("=" * 60)
    print("测试生产者")
    print("=" * 60)

    try:
        connection = await aio_pika.connect_robust(
            "amqp://admin:admin@localhost:5672",
        )

        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            "biteagle",
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )

        # 创建测试消息
        message = aio_pika.Message(
            b'{"news_id": 999, "priority": 5}',
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            priority=5,
        )

        await exchange.publish(message, routing_key="biteagle_analysis")

        print(f"✅ 消息发送成功")
        print(f"   查看 RabbitMQ 管理界面: http://localhost:15672")

        await connection.close()
        return True

    except Exception as e:
        print(f"❌ 生产者测试失败: {e}")
        return False


async def main():
    results = []

    # 测试 RabbitMQ
    results.append(await test_rabbitmq())

    # 测试 Redis
    results.append(await test_redis())

    # 测试生产者
    results.append(await test_producer())

    print()
    print("=" * 60)
    if all(results):
        print("✅ 所有测试通过！")
        return 0
    else:
        print(f"❌ 部分测试失败（{sum(results)}/{len(results)} 通过）")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
