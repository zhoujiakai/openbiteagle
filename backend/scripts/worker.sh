#!/usr/bin/env bash
# RabbitMQ Worker startup script

set -e

# Change to script directory
cd "$(dirname "$0")/.."

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Starting Biteagle RabbitMQ Worker..."
echo "RabbitMQ URL: ${RABBITMQ_URL:-amqp://admin:admin@localhost:5672}"
echo "Redis URL: ${REDIS_URL:-redis://localhost:6380}"

# Run the worker
python -m tasks.task3_mq_driven.worker "$@"
