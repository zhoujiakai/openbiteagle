"""Neo4j client for knowledge graph operations."""

from dataclasses import dataclass
from typing import Any, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseSettings):
    """Neo4j configuration settings."""

    model_config = SettingsConfigDict(env_prefix="NEO4J_", env_file=".env")

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "biteagle_password"
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60


@dataclass
class Neo4jClient:
    """Neo4j client wrapper for async operations."""

    settings: Neo4jSettings
    driver: Optional[AsyncDriver] = None

    @classmethod
    async def create(cls, settings: Optional[Neo4jSettings] = None) -> "Neo4jClient":
        """Create a new Neo4j client instance.

        Args:
            settings: Neo4j settings, defaults to environment variables

        Returns:
            Neo4jClient instance
        """
        if settings is None:
            settings = Neo4jSettings()
        client = cls(settings=settings)
        await client.connect()
        return client

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        self.driver = AsyncGraphDatabase.driver(
            self.settings.uri,
            auth=(self.settings.user, self.settings.password),
            max_connection_lifetime=self.settings.max_connection_lifetime,
            max_connection_pool_size=self.settings.max_connection_pool_size,
            connection_acquisition_timeout=self.settings.connection_acquisition_timeout,
        )
        # Verify connection
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
