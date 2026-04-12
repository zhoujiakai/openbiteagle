"""Tests for Knowledge Graph module."""

import pytest

from app.core.config import cfg
from app.kg.client import Neo4jClient
from app.kg.loader import GraphLoader
from app.kg.models import (
    ProjectNode,
    TokenNode,
)
from app.kg.query import GraphQuery


@pytest.mark.asyncio
async def test_neo4j_settings():
    """Test Neo4j settings can be loaded."""
    assert cfg.neo4j.NEO4J_URI == "bolt://localhost:7687"
    assert cfg.neo4j.NEO4J_USER == "neo4j"


@pytest.mark.asyncio
async def test_project_node_to_dict():
    """Test ProjectNode conversion to dict."""
    project = ProjectNode(
        name="Test Project",
        description="A test project",
        website="https://example.com",
    )
    data = project.to_dict()
    assert data["name"] == "Test Project"
    assert data["description"] == "A test project"
    assert data["website"] == "https://example.com"


@pytest.mark.asyncio
async def test_token_node_to_dict():
    """Test TokenNode conversion to dict."""
    token = TokenNode(
        symbol="TEST",
        name="Test Token",
        contract_address="0x123",
        chain="Ethereum",
    )
    data = token.to_dict()
    assert data["symbol"] == "TEST"
    assert data["name"] == "Test Token"
    assert data["contract_address"] == "0x123"
    assert data["chain"] == "Ethereum"


@pytest.mark.asyncio
async def test_graph_query_class():
    """Test GraphQuery class initialization."""
    # Mock client for testing
    class MockClient:
        async def execute_query(self, query, params=None):
            return []

    mock_client = MockClient()
    query_service = GraphQuery(mock_client)
    assert query_service.client is not None


@pytest.mark.asyncio
async def test_graph_loader_class():
    """Test GraphLoader class initialization."""
    # Mock client for testing
    class MockClient:
        async def execute_query(self, query, params=None):
            return []

    mock_client = MockClient()
    loader = GraphLoader(mock_client)
    assert loader.client is not None


# Integration tests (require Neo4j to be running)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_connection():
    """Test connection to Neo4j."""
    client = Neo4jClient()
    try:
        await client.connect()
        assert await client.verify_connectivity() is True
    finally:
        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_query_project():
    """Test creating and querying a project."""
    client = Neo4jClient()
    try:
        await client.connect()
        loader = GraphLoader(client)
        query_service = GraphQuery(client)

        # Create test project
        project = ProjectNode(
            name="Test Project KG",
            description="Integration test project",
        )
        await loader.create_project(project)

        # Query it back
        result = await query_service.get_project_by_name("Test Project KG")
        assert result is not None
        assert result["name"] == "Test Project KG"

    finally:
        await client.close()
