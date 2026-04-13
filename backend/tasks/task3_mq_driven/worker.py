"""RabbitMQ Worker — 新闻分析任务消费者。

从 analysis 队列消费消息，执行 LangGraph 分析流水线，
将结果持久化到数据库。支持幂等、并发控制、指数退避重试和死信队列。

用法::

    python -m tasks.task3_mq_driven.worker
"""

import asyncio
import json
import logging
import signal
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

import aio_pika
import aio_pika.abc
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import cfg
from app.data.db import AsyncSessionLocal
from app.graph import get_graph
from tasks.task2_analyze_flow.graph import get_tracing_config
from app.models.analysis import Analysis
from app.models.news import News

logger = logging.getLogger("biteagle.worker")


class Worker:
    """RabbitMQ 消费者，驱动新闻分析 LangGraph 流水线。"""

    def __init__(self) -> None:
        self._connection: Optional[aio_pika.RobustConnection] = None  # RabbitMQ 连接
        self._channel: Optional[aio_pika.RobustChannel] = None  # RabbitMQ 通道
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None  # RabbitMQ 交换机
        self._redis: Optional[aioredis.Redis] = None  # Redis 客户端，用于幂等锁
        self._semaphore = asyncio.Semaphore(cfg.worker.CONCURRENCY)  # 并发信号量，控制同时处理的消息数
        self._closing = False  # 关闭标志，用于优雅停机时阻止新操作

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """连接 RabbitMQ、Redis 并开始消费消息。"""
        self._redis = aioredis.from_url(cfg.redis.REDIS_URL)

        self._connection = await aio_pika.connect_robust(cfg.rabbitmq.RABBITMQ_URL)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=cfg.worker.CONCURRENCY)

        exchange_name = "biteagle"
        self._exchange = await self._channel.declare_exchange(
            exchange_name,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )

        # 主队列，绑定死信队列参数
        main_queue = await self._channel.declare_queue(
            cfg.rabbitmq.RABBITMQ_QUEUE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": exchange_name,
                "x-dead-letter-routing-key": cfg.rabbitmq.RABBITMQ_DLQ,
            },
        )
        await main_queue.bind(self._exchange, cfg.rabbitmq.RABBITMQ_QUEUE)

        # 死信队列
        dlq = await self._channel.declare_queue(cfg.rabbitmq.RABBITMQ_DLQ, durable=True)
        await dlq.bind(self._exchange, cfg.rabbitmq.RABBITMQ_DLQ)

        logger.info(
            "Worker 已启动  queue=%s  concurrency=%d  max_retries=%d",
            cfg.rabbitmq.RABBITMQ_QUEUE,
            cfg.worker.CONCURRENCY,
            cfg.worker.MAX_RETRIES,
        )

        await main_queue.consume(self._on_message)

    async def stop(self) -> None:
        """优雅关闭所有连接。"""
        self._closing = True
        if self._connection is not None:
            await self._connection.close()
        if self._redis is not None:
            await self._redis.close()
        logger.info("Worker 已停止")

    # ------------------------------------------------------------------
    # 消息处理
    # ------------------------------------------------------------------

    async def _on_message(
        self,
        message: aio_pika.abc.AbstractIncomingMessage,
    ) -> None:
        """每条消息的回调入口，受信号量控制并发。"""
        async with self._semaphore:
            await self._process_message(message)

    async def _process_message(
        self,
        message: aio_pika.abc.AbstractIncomingMessage,
    ) -> None:
        """解析、校验并执行单条分析任务。"""
        news_id: Optional[int] = None
        try:
            body = json.loads(message.body.decode())
            news_id = body.get("news_id")
            priority = body.get("priority", 5)

            if news_id is None:
                logger.warning("消息缺少 news_id，丢弃: %s", body)
                await message.ack()
                return

            logger.info("收到任务  news_id=%d  priority=%d", news_id, priority)

            # 幂等检查：Redis 分布式锁
            redis_key = f"biteagle:task:{news_id}"
            acquired = await self._redis.set(
                redis_key, "processing", nx=True, ex=cfg.worker.TASK_TTL
            )
            if not acquired:
                # 锁已存在，说明正在处理中或锁未过期
                current = await self._redis.get(redis_key)
                if current and current.decode() == "processing":
                    logger.info("任务正在处理中，跳过  news_id=%d", news_id)
                    await message.ack()
                    return

            # 幂等检查：数据库状态
            async with AsyncSessionLocal() as session:
                analysis = await self._find_analysis(session, news_id)
                if analysis is not None and analysis.status in ("completed", "processing"):
                    logger.info(
                        "分析已处于 %s 状态，跳过  news_id=%d",
                        analysis.status,
                        news_id,
                    )
                    await message.ack()
                    return

                # 标记为 processing
                if analysis is not None:
                    analysis.status = "processing"
                    await session.commit()

            # 执行 LangGraph 分析流水线
            result = await self._run_pipeline(news_id)

            # 保存成功结果
            await self._save_success(news_id, result)

            # 释放 Redis 锁
            await self._redis.delete(redis_key)
            await message.ack()

            logger.info("任务完成  news_id=%d", news_id)

        except Exception as exc:
            logger.error(
                "任务失败  news_id=%s  error=%s",
                news_id,
                exc,
            )
            traceback.print_exc()

            # 判断是否需要重试
            retry_count = 0
            if news_id is not None:
                retry_count = await self._handle_failure(news_id, exc)

            if news_id is not None and retry_count < cfg.worker.MAX_RETRIES:
                # 指数退避后重新投递到队列
                delay = cfg.worker.RETRY_BASE_DELAY * (2 ** (retry_count - 1)) if retry_count > 0 else cfg.worker.RETRY_BASE_DELAY
                logger.info(
                    "准备重试  news_id=%d  retry=%d/%d  delay=%ds",
                    news_id,
                    retry_count,
                    cfg.worker.MAX_RETRIES,
                    delay,
                )
                asyncio.create_task(
                    self._requeue_with_delay(message, news_id, delay)
                )
            else:
                # 超过最大重试次数，NACK 进入死信队列
                if news_id is not None:
                    logger.error(
                        "超过最大重试次数，转入死信队列  news_id=%d", news_id
                    )
                    await self._mark_failed(news_id, str(exc), retry_count)
                    redis_key = f"biteagle:task:{news_id}"
                    await self._redis.delete(redis_key)
                await message.nack(requeue=False)

    # ------------------------------------------------------------------
    # 分析流水线
    # ------------------------------------------------------------------

    async def _run_pipeline(self, news_id: int) -> dict[str, Any]:
        """获取新闻数据并执行 LangGraph news_analysis 流水线。"""
        graph = get_graph("news_analysis")

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(News).where(News.id == news_id)
            )
            news = result.scalar_one_or_none()
            if news is None:
                raise ValueError(f"News {news_id} not found")

            title = news.title
            content = news.content or ""

        input_state = {
            "news_id": news_id,
            "title": title,
            "content": content,
        }

        metadata = {
            "news_id": str(news_id),
            "news_title": title[:50],
        }
        config = get_tracing_config(metadata)
        config["run_name"] = f"worker_analysis_{news_id}"

        return await graph.ainvoke(input_state, config=config)

    # ------------------------------------------------------------------
    # 数据持久化
    # ------------------------------------------------------------------

    async def _find_analysis(
        self, session: AsyncSession, news_id: int
    ) -> Optional[Analysis]:
        """根据 news_id 查找已有的 analysis 记录。"""
        result = await session.execute(
            select(Analysis).where(Analysis.news_id == news_id)
        )
        return result.scalar_one_or_none()

    async def _save_success(self, news_id: int, result: dict[str, Any]) -> None:
        """更新或创建分析记录，写入成功结果。"""
        async with AsyncSessionLocal() as session:
            analysis = await self._find_analysis(session, news_id)

            if analysis is None:
                analysis = Analysis(news_id=news_id)
                session.add(analysis)

            analysis.status = "completed"
            analysis.completed_at = datetime.now(timezone.utc)
            analysis.investment_value = result.get("investment_value")
            analysis.confidence = result.get("investment_confidence")
            analysis.tokens = result.get("tokens")
            analysis.trend_analysis = result.get("trend_analysis")
            analysis.recommendation = result.get("recommendation")
            analysis.steps = self._extract_steps(result)

            await session.commit()

    async def _mark_failed(
        self,
        news_id: int,
        error_message: str,
        retry_count: int,
    ) -> None:
        """将分析记录标记为失败。"""
        async with AsyncSessionLocal() as session:
            analysis = await self._find_analysis(session, news_id)

            if analysis is None:
                analysis = Analysis(
                    news_id=news_id,
                    status="failed",
                    error_message=error_message,
                    retry_count=retry_count,
                )
                session.add(analysis)
            else:
                analysis.status = "failed"
                analysis.error_message = error_message
                analysis.retry_count = retry_count

            await session.commit()

    async def _handle_failure(self, news_id: int, exc: Exception) -> int:
        """增加重试计数并返回当前次数。"""
        async with AsyncSessionLocal() as session:
            analysis = await self._find_analysis(session, news_id)

            if analysis is None:
                # 创建记录以追踪 retry_count
                analysis = Analysis(
                    news_id=news_id,
                    status="pending",
                    retry_count=1,
                    error_message=str(exc),
                )
                session.add(analysis)
                await session.commit()
                return 1

            analysis.retry_count += 1
            analysis.error_message = str(exc)
            await session.commit()
            return analysis.retry_count

    @staticmethod
    def _extract_steps(result: dict[str, Any]) -> dict[str, Any]:
        """从流水线结果中提取各节点输出，组装为 steps 字典。"""
        steps: dict[str, Any] = {}
        node_fields = [
            ("investment_value", "investment_value"),
            ("investment_confidence", "investment_confidence"),
            ("investment_reasoning", "investment_reasoning"),
            ("tokens", "tokens"),
            ("token_details", "token_details"),
            ("rag_context", "rag_context"),
            ("rag_sources", "rag_sources"),
            ("kg_context", "kg_context"),
            ("kg_entities", "kg_entities"),
            ("trend_analysis", "trend_analysis"),
            ("recommendation", "recommendation"),
            ("risk_level", "risk_level"),
            ("recommendation_reasoning", "recommendation_reasoning"),
        ]
        for key, field in node_fields:
            if field in result and result[field] is not None:
                steps[key] = result[field]
        return steps

    # ------------------------------------------------------------------
    # 重试 / 重新入队
    # ------------------------------------------------------------------

    async def _requeue_with_delay(
        self,
        original_message: aio_pika.abc.AbstractIncomingMessage,
        news_id: int,
        delay: int,
    ) -> None:
        """等待 delay 秒后，将消息重新投递到队列。"""
        await asyncio.sleep(delay)

        if self._closing or self._exchange is None:
            return

        body = json.dumps({"news_id": news_id}).encode()
        await self._exchange.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=cfg.rabbitmq.RABBITMQ_QUEUE,
        )
        # ACK 原始消息，将其从队列移除
        await original_message.ack()
        logger.info("已重新投递任务  news_id=%d", news_id)


# ======================================================================
# 入口
# ======================================================================


async def main() -> None:
    """启动 Worker 并等待关闭信号。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(name)-20s  %(levelname)-7s  %(message)s",
    )

    worker = Worker()
    loop = asyncio.get_running_loop()

    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await worker.start()

    logger.info("Worker 运行中 — 按 Ctrl+C 停止")
    await shutdown_event.wait()

    await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
