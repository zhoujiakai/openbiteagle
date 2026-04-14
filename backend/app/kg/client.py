"""用于知识图谱操作的 Neo4j 客户端。"""

from dataclasses import dataclass
from typing import Any, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import cfg


@dataclass
class Neo4jClient:
    """Neo4j 异步操作客户端封装。"""

    driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        """建立到 Neo4j 的连接。"""
        self.driver = AsyncGraphDatabase.driver(
            cfg.neo4j.NEO4J_URI,
            auth=(cfg.neo4j.NEO4J_USER, cfg.neo4j.NEO4J_PASSWORD),
            max_connection_lifetime=cfg.neo4j.NEO4J_MAX_CONNECTION_LIFETIME,
            max_connection_pool_size=cfg.neo4j.NEO4J_MAX_CONNECTION_POOL_SIZE,
            connection_acquisition_timeout=cfg.neo4j.NEO4J_CONNECTION_ACQUISITION_TIMEOUT,
        )
        # 验证连接
        await self.verify_connectivity()

    async def verify_connectivity(self) -> bool:
        """验证到 Neo4j 的连接是否正常。

        Returns:
            连接成功返回 True
        """
        if self.driver is None:
            raise RuntimeError("Driver not initialized")
        await self.driver.verify_connectivity()
        return True

    async def close(self) -> None:
        """关闭 Neo4j 驱动连接。"""
        if self.driver:
            await self.driver.close()

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """执行 Cypher 查询。

        Args:
            query: Cypher 查询字符串
            parameters: 查询参数
            database: 数据库名称（默认为 neo4j）

        Returns:
            结果记录列表
        """
        if self.driver is None:
            raise RuntimeError("Driver not initialized")

        async with self.driver.session(database=database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> Any:
        """执行写入 Cypher 查询。

        Args:
            query: Cypher 查询字符串
            parameters: 查询参数
            database: 数据库名称（默认为 neo4j）

        Returns:
            写入操作的摘要
        """
        if self.driver is None:
            raise RuntimeError("Driver not initialized")

        async with self.driver.session(database=database) as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            return summary

    async def __aenter__(self) -> "Neo4jClient":
        """异步上下文管理器入口。"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """异步上下文管理器出口。"""
        await self.close()
