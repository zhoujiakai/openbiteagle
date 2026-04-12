#!/usr/bin/env python3
"""Simple test: Get one message from queue."""

import asyncio
import sys

import aio_pika


async def get_one_message():
    """Get one message from the queue."""
    print("=" * 60)
    print("Getting one message from queue...")
    print("=" * 60)

    connection = await aio_pika.connect_robust(
        "amqp://admin:admin@localhost:5672",
    )

    channel = await connection.channel()

    # Get queue (passive = don't create, just get existing)
    queue = await channel.get_queue("biteagle_analysis")

    # Get message count
    message_count = queue.declaration_result.message_count
    print(f"Messages in queue: {message_count}")

    if message_count > 0:
        # Fetch one message
        message = await queue.get(timeout=5)
        if message:
            print(f"\n📨 Got message:")
            print(f"   Body: {message.body.decode()}")
            await message.ack()
            print(f"   ✅ Message ACKed")
        else:
            print("   No message received")
    else:
        print("   Queue is empty")

    await connection.close()
    print("\n✅ Test complete")


if __name__ == "__main__":
    asyncio.run(get_one_message())
