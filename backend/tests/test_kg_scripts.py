"""知识图谱模块测试。"""

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
    """测试 Neo4j 配置是否可以加载。"""
    assert cfg.neo4j.NEO4J_URI == "bolt://localhost:7687"
    assert cfg.neo4j.NEO4J_USER == "neo4j"


@pytest.mark.asyncio
async def test_project_node_to_dict():
    """测试 ProjectNode 转换为字典。"""
    project = ProjectNode(
        name="测试项目",
        description="一个测试项目",
        website="https://example.com",
    )
    data = project.to_dict()
    assert data["name"] == "测试项目"
    assert data["description"] == "一个测试项目"
    assert data["website"] == "https://example.com"


@pytest.mark.asyncio
async def test_token_node_to_dict():
    """测试 TokenNode 转换为字典。"""
    token = TokenNode(
        symbol="TEST",
        name="测试代币",
        contract_address="0x123",
        chain="Ethereum",
    )
    data = token.to_dict()
    assert data["symbol"] == "TEST"
    assert data["name"] == "测试代币"
    assert data["contract_address"] == "0x123"
    assert data["chain"] == "Ethereum"


@pytest.mark.asyncio
async def test_graph_query_class():
    """测试 GraphQuery 类初始化。"""
    # 用于测试的模拟客户端
    class MockClient:
        async def execute_query(self, query, params=None):
            return []

    mock_client = MockClient()
    query_service = GraphQuery(mock_client)
    assert query_service.client is not None


@pytest.mark.asyncio
async def test_graph_loader_class():
    """测试 GraphLoader 类初始化。"""
    # 用于测试的模拟客户端
    class MockClient:
        async def execute_query(self, query, params=None):
            return []

    mock_client = MockClient()
    loader = GraphLoader(mock_client)
    assert loader.client is not None


# 集成测试（需要运行 Neo4j）
@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_connection():
    """测试连接 Neo4j。"""
    client = Neo4jClient()
    try:
        await client.connect()
        assert await client.verify_connectivity() is True
    finally:
        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_query_project():
    """测试创建和查询项目。"""
    client = Neo4jClient()
    try:
        await client.connect()
        loader = GraphLoader(client)
        query_service = GraphQuery(client)

        # 创建测试项目
        project = ProjectNode(
            name="测试项目 KG",
            description="集成测试项目",
        )
        await loader.create_project(project)

        # 查询回来
        result = await query_service.get_project_by_name("测试项目 KG")
        assert result is not None
        assert result["name"] == "测试项目 KG"

    finally:
        await client.close()
