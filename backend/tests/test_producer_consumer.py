#!/usr/bin/env python3
"""测试：发送并接收消息。"""

import asyncio
import json

import aio_pika


async def test_send_receive():
    """发送一条消息并接收它。"""
    print("=" * 60)
    print("测试 发送 -> 接收")
    print("=" * 60)

    connection = await aio_pika.connect_robust(
        "amqp://admin:admin@localhost:5672",
    )

    channel = await connection.channel()

    # 声明交换机和队列
    exchange = await channel.declare_exchange(
        "biteagle",
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    queue = await channel.declare_queue(
        "biteagle_analysis",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "biteagle",
            "x-dead-letter-routing-key": "biteagle_analysis_dlq",
        },
    )

    await queue.bind(exchange, "biteagle_analysis")

    # 发送消息
    test_data = {"news_id": 123, "priority": 5, "test": True}
    message = aio_pika.Message(
        json.dumps(test_data).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        priority=5,
    )

    await exchange.publish(message, routing_key="biteagle_analysis")
    print(f"✅ 已发送: {test_data}")

    # 接收消息
    received = await queue.get(timeout=5)
    if received:
        body = json.loads(received.body.decode())
        print(f"📨 已接收: {body}")
        await received.ack()
        print(f"✅ 消息已确认")

        # 验证
        if body == test_data:
            print("\n✅ 发送/接收测试通过！")
        else:
            print(f"\n❌ 数据不匹配: 发送 {test_data}，收到 {body}")
    else:
        print("❌ 未收到消息")

    await connection.close()


if __name__ == "__main__":
    asyncio.run(test_send_receive())
