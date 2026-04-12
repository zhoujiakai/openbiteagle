#!/usr/bin/env python3
"""Quick test RabbitMQ and Redis connection."""

import asyncio
import sys

import aio_pika
import redis.asyncio as aioredis


async def test_rabbitmq():
    """Test RabbitMQ connection."""
    print("=" * 60)
    print("Testing RabbitMQ Connection")
    print("=" * 60)
    print("URL: amqp://admin:admin@localhost:5672")
    print()

    try:
        connection = await aio_pika.connect_robust(
            "amqp://admin:admin@localhost:5672",
            reconnect_interval=5,
        )

        # Create channel
        channel = await connection.channel()

        # Declare exchange
        exchange = await channel.declare_exchange(
            "biteagle",
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )

        # Declare queues
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

        # Bind queues
        await main_queue.bind(exchange, "biteagle_analysis")
        await dlq_queue.bind(exchange, "biteagle_analysis_dlq")

        print(f"✅ RabbitMQ connection successful")
        print(f"   Exchange: {exchange.name}")
        print(f"   Main Queue: {main_queue.name}")
        print(f"   DLQ: {dlq_queue.name}")

        await connection.close()
        return True

    except Exception as e:
        print(f"❌ RabbitMQ connection failed: {e}")
        return False


async def test_redis():
    """Test Redis connection."""
    print()
    print("=" * 60)
    print("Testing Redis Connection")
    print("=" * 60)
    print("URL: redis://localhost:6380")
    print()

    try:
        client = aioredis.from_url("redis://localhost:6380")
        await client.ping()
        print("✅ Redis connection successful")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


async def test_producer():
    """Test sending a message."""
    print()
    print("=" * 60)
    print("Testing Producer")
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

        # Create test message
        message = aio_pika.Message(
            b'{"news_id": 999, "priority": 5}',
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            priority=5,
        )

        await exchange.publish(message, routing_key="biteagle_analysis")

        print(f"✅ Message sent successfully")
        print(f"   Check RabbitMQ management: http://localhost:15672")

        await connection.close()
        return True

    except Exception as e:
        print(f"❌ Producer test failed: {e}")
        return False


async def main():
    results = []

    # Test RabbitMQ
    results.append(await test_rabbitmq())

    # Test Redis
    results.append(await test_redis())

    # Test Producer
    results.append(await test_producer())

    print()
    print("=" * 60)
    if all(results):
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ Some tests failed ({sum(results)}/{len(results)} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
