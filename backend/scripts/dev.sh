#!/bin/bash
# 开发环境启动脚本

set -e

# 激活 conda 环境
echo "激活 conda 环境: biteagle..."
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate biteagle

# 安装依赖
echo "检查并安装依赖..."
pip install -q -r requirements.txt

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，从 .env.example 复制..."
    cp .env.example .env
fi

# 启动服务
echo "启动 FastAPI 服务..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
