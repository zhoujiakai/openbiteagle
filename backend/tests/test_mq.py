#!/usr/bin/env python3
"""测试 RabbitMQ 和 Redis 连接。

用法:
    python tests/test_mq.py [--connection] [--producer] [--cache]
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import cfg
from app.data.cache import get_cache
from app.data.rabbit import get_rabbit


async def test_rabbitmq():
    """测试 RabbitMQ 连接。"""
    print("=" * 60)
    print("测试 RabbitMQ 连接")
    print("=" * 60)
    print(f"URL: {cfg.rabbitmq.RABBITMQ_URL}")
    print(f"队列: {cfg.rabbitmq.RABBITMQ_QUEUE}")
    print(f"死信队列: {cfg.rabbitmq.RABBITMQ_DLQ}")
    print()

    try:
        rabbit = await get_rabbit()
        print("✅ RabbitMQ 连接成功")
        print(f"   交换机: biteagle")
        print(f"   主队列: {cfg.rabbitmq.RABBITMQ_QUEUE}")
        print(f"   死信队列: {cfg.rabbitmq.RABBITMQ_DLQ}")
        return True
    except Exception as e:
        print(f"❌ RabbitMQ 连接失败: {e}")
        return False


async def test_cache():
    """测试 Redis 连接。"""
    print()
    print("=" * 60)
    print("测试 Redis 缓存")
    print("=" * 60)
    print(f"URL: {cfg.redis.REDIS_URL}")
    print()

    try:
        cache = await get_cache()
        # 测试 set/get
        await cache.set("test:ping", "pong", expire=10)
        value = await cache.get("test:ping", str)

        if value == "pong":
            print("✅ Redis 连接成功")
            print(f"   Set/Get 测试通过")
            # 清理
            await cache.delete("test:ping")
            return True
        else:
            print(f"❌ Redis 测试失败: 期望 'pong'，得到 '{value}'")
            return False
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False


async def test_producer(news_id: int = 999):
    """测试向 RabbitMQ 发送消息。"""
    print()
    print("=" * 60)
    print("测试生产者")
    print("=" * 60)
    print(f"发送测试消息: news_id={news_id}")
    print()

    try:
        rabbit = await get_rabbit()
        test_data = {"news_id": news_id, "priority": 5, "test": True}
        await rabbit.send(cfg.rabbitmq.RABBITMQ_QUEUE, test_data)

        print(f"✅ 消息发送成功")
        print(f"   查看 RabbitMQ 管理界面: http://localhost:15672")
        return True
    except Exception as e:
        print(f"❌ 生产者出错: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="测试基础设施配置")
    parser.add_argument("--connection", action="store_true", help="仅测试连接")
    parser.add_argument("--producer", action="store_true", help="测试生产者")
    parser.add_argument("--cache", action="store_true", help="测试缓存/Redis")
    parser.add_argument("--news-id", type=int, default=999, help="测试新闻 ID")

    args = parser.parse_args()

    # 如果未指定特定测试，则运行所有测试
    run_all = not any([args.connection, args.producer, args.cache])

    results = []

    # 测试 RabbitMQ
    if run_all or args.connection:
        results.append(await test_rabbitmq())

    # 测试 Redis/缓存
    if run_all or args.cache:
        results.append(await test_cache())

    # 测试生产者
    if run_all or args.producer:
        results.append(await test_producer(args.news_id))

    # 清理
    from app.data.rabbit import close_rabbit
    from app.data.cache import close_cache
    await close_rabbit()
    await close_cache()

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
