#!/usr/bin/env python3
"""Test RabbitMQ consumer (listens for one message)."""

import asyncio
import sys

import aio_pika


async def listen_one_message():
    """Listen for one message from the queue."""
    print("=" * 60)
    print("Listening for messages (press Ctrl+C to stop)...")
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
                print(f"📨 Message #{message_count}")
                print(f"   Body: {message.body.decode()}")
                print()

                if message_count >= 3:  # Process up to 3 messages
                    print("✅ Processed 3 messages, stopping...")
                    break

    await connection.close()
    print(f"\n✅ Total messages processed: {message_count}")


if __name__ == "__main__":
    try:
        asyncio.run(listen_one_message())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(0)
