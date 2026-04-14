"""知识图谱 API 端点。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.kg.client import Neo4jClient
from app.kg.loader import GraphLoader
from app.kg.models import (
    ChainNode,
    ProjectNode,
    TokenNode,
)
from app.kg.query import GraphQuery

router = APIRouter(prefix="/kg", tags=["knowledge-graph"])


async def get_neo4j_client() -> Neo4jClient:
    """获取 Neo4j 客户端的依赖注入。"""
    client = Neo4jClient()
    await client.connect()
    try:
        yield client
    finally:
        await client.close()


async def get_graph_query(
    client: Neo4jClient = Depends(get_neo4j_client),
) -> GraphQuery:
    """获取图查询服务的依赖注入。"""
    return GraphQuery(client)


async def get_graph_loader(
    client: Neo4jClient = Depends(get_neo4j_client),
) -> GraphLoader:
    """获取图加载器服务的依赖注入。"""
    return GraphLoader(client)


@router.get("/stats")
async def get_graph_stats(
    service: GraphQuery = Depends(get_graph_query),
) -> dict[str, Any]:
    """获取知识图谱统计信息。

    返回图谱中各节点类型的数量。
    """
    return await service.get_graph_stats()


@router.get("/projects/{project_name}")
async def get_project(
    project_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> dict[str, Any]:
    """获取项目信息。

    Args:
        project_name: 项目名称

    Returns:
        项目节点数据
    """
    project = await service.get_project_by_name(project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_name}/context")
async def get_project_context(
    project_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> dict[str, Any]:
    """获取项目的完整上下文。

    包括代币、团队、投资方、公链和合作。

    Args:
        project_name: 项目名称

    Returns:
        完整的项目上下文
    """
    context = await service.get_project_context(project_name)
    if not context or not context.get("project"):
        raise HTTPException(status_code=404, detail="Project not found")
    return context


@router.get("/projects/{project_name}/tokens")
async def get_project_tokens(
    project_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """获取项目发行的代币。

    Args:
        project_name: 项目名称

    Returns:
        代币节点列表
    """
    return await service.get_project_tokens(project_name)


@router.get("/projects/{project_name}/team")
async def get_project_team(
    project_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """获取项目的团队成员。

    Args:
        project_name: 项目名称

    Returns:
        包含角色信息的人物节点列表
    """
    return await service.get_project_team(project_name)


@router.get("/projects/{project_name}/investors")
async def get_project_investors(
    project_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """获取项目的投资方。

    Args:
        project_name: 项目名称

    Returns:
        包含投资详情的机构节点列表
    """
    return await service.get_project_investors(project_name)


@router.get("/projects/{project_name}/related")
async def get_related_projects(
    project_name: str,
    max_hops: int = Query(2, ge=1, le=3),
    limit: int = Query(20, ge=1, le=100),
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """查找通过投资方、团队或合作关联的项目。

    Args:
        project_name: 起始项目名称
        max_hops: 最大关系跳数（1-3）
        limit: 最大结果数（1-100）

    Returns:
        包含路径信息的关联项目列表
    """
    return await service.find_related_projects(project_name, max_hops, limit)


@router.get("/tokens/{symbol}")
async def get_token(
    symbol: str,
    service: GraphQuery = Depends(get_graph_query),
) -> dict[str, Any]:
    """获取代币信息及其关联项目。

    Args:
        symbol: 代币符号

    Returns:
        包含项目信息的代币节点
    """
    token = await service.get_token_info(symbol)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return token


@router.get("/institutions/{institution_name}/portfolio")
async def get_institution_portfolio(
    institution_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """获取投资机构的投资组合。

    Args:
        institution_name: 机构名称

    Returns:
        项目节点列表
    """
    return await service.get_institution_portfolio(institution_name)


@router.get("/persons/{person_name}/projects")
async def get_person_projects(
    person_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """获取与某人物关联的项目。

    Args:
        person_name: 人物名称

    Returns:
        包含关系详情的项目节点列表
    """
    return await service.get_person_projects(person_name)


@router.get("/chains/{chain_name}/projects")
async def get_chain_projects(
    chain_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """获取特定公链上的项目。

    Args:
        chain_name: 公链名称

    Returns:
        项目节点列表
    """
    return await service.get_chain_projects(chain_name)


@router.get("/search")
async def search_projects(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """按关键词搜索项目。

    Args:
        keyword: 搜索关键词
        limit: 最大结果数

    Returns:
        匹配的项目节点列表
    """
    return await service.search_projects_by_keyword(keyword, limit)


@router.post("/init")
async def initialize_graph(
    loader: GraphLoader = Depends(get_graph_loader),
) -> dict[str, str]:
    """初始化图约束。

    为所有节点类型创建唯一约束。
    """
    await loader.create_constraints()
    return {"status": "success", "message": "Graph constraints initialized"}


@router.post("/projects")
async def create_project(
    project: ProjectNode,
    chain: str | None = None,
    loader: GraphLoader = Depends(get_graph_loader),
) -> dict[str, Any]:
    """创建新的项目节点。

    Args:
        project: 项目数据
        chain: 可选的公链名称

    Returns:
        创建的节点数据
    """
    result = await loader.create_project(project)
    if chain:
        await loader.create_chain(ChainNode(name=chain))
        await loader.relate_project_to_chain(project.name, chain)
    return result


@router.post("/projects/full")
async def create_full_project(
    project: ProjectNode,
    chain: str | None = None,
    tokens: list[TokenNode] | None = None,
    loader: GraphLoader = Depends(get_graph_loader),
) -> dict[str, str]:
    """创建项目及其所有关系。

    Args:
        project: 项目数据
        chain: 可选的公链名称
        tokens: 可选的代币列表

    Returns:
        状态消息
    """
    await loader.create_full_project(project, chain=chain, tokens=tokens)
    return {"status": "success", "message": f"Project {project.name} created"}
