#!/usr/bin/env python3
"""测试 RabbitMQ 消费者（监听消息）。"""

import asyncio
import sys

import aio_pika


async def listen_one_message():
    """从队列中监听消息。"""
    print("=" * 60)
    print("正在监听消息（按 Ctrl+C 停止）...")
    print("=" * 60)
    print()

    connection = await aio_pika.connect_robust(
        "amqp://admin:admin@localhost:5672",
    )

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    queue = await channel.declare_queue(
        "biteagle_analysis",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "biteagle",
            "x-dead-letter-routing-key": "biteagle_analysis_dlq",
        },
    )

    message_count = 0

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                message_count += 1
                print(f"📨 消息 #{message_count}")
                print(f"   内容: {message.body.decode()}")
                print()

                if message_count >= 3:  # 最多处理 3 条消息
                    print("✅ 已处理 3 条消息，停止监听...")
                    break

    await connection.close()
    print(f"\n✅ 共处理 {message_count} 条消息")


if __name__ == "__main__":
    try:
        asyncio.run(listen_one_message())
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(0)
