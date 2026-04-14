"""Neo4j client for knowledge graph operations."""

from dataclasses import dataclass
from typing import Any, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import cfg


@dataclass
class Neo4jClient:
    """Neo4j client wrapper for async operations."""

    driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
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
        """Verify that the connection to Neo4j is working.

        Returns:
            True if connection is successful
        """
        if self.driver is None:
            raise RuntimeError("Driver not initialized")
        await self.driver.verify_connectivity()
        return True

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self.driver:
            await self.driver.close()

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (defaults to neo4j)

        Returns:
            List of result records
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
        """Execute a write Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (defaults to neo4j)

        Returns:
            Summary of the write operation
        """
        if self.driver is None:
            raise RuntimeError("Driver not initialized")

        async with self.driver.session(database=database) as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            return summary

    async def __aenter__(self) -> "Neo4jClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Async context manager exit."""
        await self.close()
