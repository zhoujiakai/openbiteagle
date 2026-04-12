"""Knowledge Graph API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.kg.client import Neo4jClient, Neo4jSettings
from app.kg.loader import GraphLoader
from app.kg.models import (
    ChainNode,
    ProjectNode,
    TokenNode,
)
from app.kg.query import GraphQuery

router = APIRouter(prefix="/kg", tags=["knowledge-graph"])


async def get_neo4j_client() -> Neo4jClient:
    """Dependency to get Neo4j client."""
    settings = Neo4jSettings()
    client = await Neo4jClient.create(settings)
    try:
        yield client
    finally:
        await client.close()


async def get_graph_query(
    client: Neo4jClient = Depends(get_neo4j_client),
) -> GraphQuery:
    """Dependency to get graph query service."""
    return GraphQuery(client)


async def get_graph_loader(
    client: Neo4jClient = Depends(get_neo4j_client),
) -> GraphLoader:
    """Dependency to get graph loader service."""
    return GraphLoader(client)


@router.get("/stats")
async def get_graph_stats(
    service: GraphQuery = Depends(get_graph_query),
) -> dict[str, Any]:
    """Get knowledge graph statistics.

    Returns counts of each node type in the graph.
    """
    return await service.get_graph_stats()


@router.get("/projects/{project_name}")
async def get_project(
    project_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> dict[str, Any]:
    """Get project information.

    Args:
        project_name: Project name

    Returns:
        Project node data
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
    """Get full context for a project.

    Includes tokens, team, investors, chain, and collaborations.

    Args:
        project_name: Project name

    Returns:
        Complete project context
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
    """Get tokens issued by a project.

    Args:
        project_name: Project name

    Returns:
        List of token nodes
    """
    return await service.get_project_tokens(project_name)


@router.get("/projects/{project_name}/team")
async def get_project_team(
    project_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """Get team members of a project.

    Args:
        project_name: Project name

    Returns:
        List of person nodes with roles
    """
    return await service.get_project_team(project_name)


@router.get("/projects/{project_name}/investors")
async def get_project_investors(
    project_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """Get investors of a project.

    Args:
        project_name: Project name

    Returns:
        List of institution nodes with investment details
    """
    return await service.get_project_investors(project_name)


@router.get("/projects/{project_name}/related")
async def get_related_projects(
    project_name: str,
    max_hops: int = Query(2, ge=1, le=3),
    limit: int = Query(20, ge=1, le=100),
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """Find projects related through investors, team, or collaborations.

    Args:
        project_name: Starting project name
        max_hops: Maximum relationship hops (1-3)
        limit: Maximum results (1-100)

    Returns:
        List of related projects with path information
    """
    return await service.find_related_projects(project_name, max_hops, limit)


@router.get("/tokens/{symbol}")
async def get_token(
    symbol: str,
    service: GraphQuery = Depends(get_graph_query),
) -> dict[str, Any]:
    """Get token information with associated project.

    Args:
        symbol: Token symbol

    Returns:
        Token node with project information
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
    """Get portfolio of an investment institution.

    Args:
        institution_name: Institution name

    Returns:
        List of project nodes
    """
    return await service.get_institution_portfolio(institution_name)


@router.get("/persons/{person_name}/projects")
async def get_person_projects(
    person_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """Get projects associated with a person.

    Args:
        person_name: Person name

    Returns:
        List of project nodes with relationship details
    """
    return await service.get_person_projects(person_name)


@router.get("/chains/{chain_name}/projects")
async def get_chain_projects(
    chain_name: str,
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """Get projects on a specific chain.

    Args:
        chain_name: Chain name

    Returns:
        List of project nodes
    """
    return await service.get_chain_projects(chain_name)


@router.get("/search")
async def search_projects(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    service: GraphQuery = Depends(get_graph_query),
) -> list[dict[str, Any]]:
    """Search projects by keyword.

    Args:
        keyword: Search keyword
        limit: Maximum results

    Returns:
        List of matching project nodes
    """
    return await service.search_projects_by_keyword(keyword, limit)


@router.post("/init")
async def initialize_graph(
    loader: GraphLoader = Depends(get_graph_loader),
) -> dict[str, str]:
    """Initialize graph constraints.

    Creates unique constraints for all node types.
    """
    await loader.create_constraints()
    return {"status": "success", "message": "Graph constraints initialized"}


@router.post("/projects")
async def create_project(
    project: ProjectNode,
    chain: str | None = None,
    loader: GraphLoader = Depends(get_graph_loader),
) -> dict[str, Any]:
    """Create a new project node.

    Args:
        project: Project data
        chain: Optional chain name

    Returns:
        Created node data
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
    """Create a project with all its relationships.

    Args:
        project: Project data
        chain: Optional chain name
        tokens: Optional list of tokens

    Returns:
        Status message
    """
    await loader.create_full_project(project, chain=chain, tokens=tokens)
    return {"status": "success", "message": f"Project {project.name} created"}
