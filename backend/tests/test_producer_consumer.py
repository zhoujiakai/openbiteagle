#!/usr/bin/env python3
"""Test: Send and receive message."""

import asyncio
import json

import aio_pika


async def test_send_receive():
    """Send a message and receive it."""
    print("=" * 60)
    print("Testing Send -> Receive")
    print("=" * 60)

    connection = await aio_pika.connect_robust(
        "amqp://admin:admin@localhost:5672",
    )

    channel = await connection.channel()

    # Declare exchange and queue
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

    # Send message
    test_data = {"news_id": 123, "priority": 5, "test": True}
    message = aio_pika.Message(
        json.dumps(test_data).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        priority=5,
    )

    await exchange.publish(message, routing_key="biteagle_analysis")
    print(f"✅ Sent: {test_data}")

    # Receive message
    received = await queue.get(timeout=5)
    if received:
        body = json.loads(received.body.decode())
        print(f"📨 Received: {body}")
        await received.ack()
        print(f"✅ Message ACKed")

        # Verify
        if body == test_data:
            print("\n✅ Send/Receive test PASSED!")
        else:
            print(f"\n❌ Data mismatch: sent {test_data}, got {body}")
    else:
        print("❌ No message received")

    await connection.close()


if __name__ == "__main__":
    asyncio.run(test_send_receive())
