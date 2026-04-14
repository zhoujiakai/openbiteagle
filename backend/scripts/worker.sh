#!/usr/bin/env bash
# RabbitMQ Worker 启动脚本

set -e

# 切换到脚本所在目录
cd "$(dirname "$0")/.."

# 激活虚拟环境（如果存在）
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "正在启动 Biteagle RabbitMQ Worker..."
echo "RabbitMQ URL: ${RABBITMQ_URL:-amqp://admin:admin@localhost:5672}"
echo "Redis URL: ${REDIS_URL:-redis://localhost:6380}"

# 运行 Worker
python -m tasks.task3_mq_driven.worker "$@"
