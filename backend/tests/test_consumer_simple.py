#!/usr/bin/env python3
"""简单测试：从队列获取一条消息。"""

import asyncio
import sys

import aio_pika


async def get_one_message():
    """从队列中获取一条消息。"""
    print("=" * 60)
    print("正在从队列获取一条消息...")
    print("=" * 60)

    connection = await aio_pika.connect_robust(
        "amqp://admin:admin@localhost:5672",
    )

    channel = await connection.channel()

    # 获取队列（passive = 不创建，仅获取已有的）
    queue = await channel.get_queue("biteagle_analysis")

    # 获取消息数量
    message_count = queue.declaration_result.message_count
    print(f"队列中的消息数: {message_count}")

    if message_count > 0:
        # 取一条消息
        message = await queue.get(timeout=5)
        if message:
            print(f"\n📨 收到消息:")
            print(f"   内容: {message.body.decode()}")
            await message.ack()
            print(f"   ✅ 消息已确认")
        else:
            print("   未收到消息")
    else:
        print("   队列为空")

    await connection.close()
    print("\n✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(get_one_message())
