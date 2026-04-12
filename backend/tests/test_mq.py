#!/usr/bin/env python3
"""Test RabbitMQ and Redis connections.

Usage:
    python scripts/test_mq.py [--connection] [--producer] [--cache]
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.data.cache import get_cache
from app.data.rabbit import get_rabbit


async def test_rabbitmq():
    """Test RabbitMQ connection."""
    print("=" * 60)
    print("Testing RabbitMQ Connection")
    print("=" * 60)
    print(f"URL: {settings.RABBITMQ_URL}")
    print(f"Queue: {settings.RABBITMQ_QUEUE}")
    print(f"DLQ: {settings.RABBITMQ_DLQ}")
    print()

    try:
        rabbit = await get_rabbit()
        print("✅ RabbitMQ connection successful")
        print(f"   Exchange: biteagle")
        print(f"   Main Queue: {settings.RABBITMQ_QUEUE}")
        print(f"   DLQ: {settings.RABBITMQ_DLQ}")
        return True
    except Exception as e:
        print(f"❌ RabbitMQ connection failed: {e}")
        return False


async def test_cache():
    """Test Redis connection."""
    print()
    print("=" * 60)
    print("Testing Redis Cache")
    print("=" * 60)
    print(f"URL: {settings.REDIS_URL}")
    print()

    try:
        cache = await get_cache()
        # Test set/get
        await cache.set("test:ping", "pong", expire=10)
        value = await cache.get("test:ping", str)

        if value == "pong":
            print("✅ Redis connection successful")
            print(f"   Set/Get test passed")
            # Cleanup
            await cache.delete("test:ping")
            return True
        else:
            print(f"❌ Redis test failed: expected 'pong', got '{value}'")
            return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


async def test_producer(news_id: int = 999):
    """Test sending a message to RabbitMQ."""
    print()
    print("=" * 60)
    print("Testing Producer")
    print("=" * 60)
    print(f"Sending test message: news_id={news_id}")
    print()

    try:
        rabbit = await get_rabbit()
        test_data = {"news_id": news_id, "priority": 5, "test": True}
        await rabbit.send(settings.RABBITMQ_QUEUE, test_data)

        print(f"✅ Message sent successfully")
        print(f"   Check RabbitMQ management: http://localhost:15672")
        return True
    except Exception as e:
        print(f"❌ Producer error: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test infrastructure setup")
    parser.add_argument("--connection", action="store_true", help="Test connection only")
    parser.add_argument("--producer", action="store_true", help="Test producer")
    parser.add_argument("--cache", action="store_true", help="Test cache/Redis")
    parser.add_argument("--news-id", type=int, default=999, help="Test news ID")

    args = parser.parse_args()

    # Run all tests if no specific test selected
    run_all = not any([args.connection, args.producer, args.cache])

    results = []

    # Test RabbitMQ
    if run_all or args.connection:
        results.append(await test_rabbitmq())

    # Test Redis/Cache
    if run_all or args.cache:
        results.append(await test_cache())

    # Test Producer
    if run_all or args.producer:
        results.append(await test_producer(args.news_id))

    # Cleanup
    from app.data.rabbit import close_rabbit
    from app.data.cache import close_cache
    await close_rabbit()
    await close_cache()

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
