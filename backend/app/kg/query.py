"""Graph query functions for knowledge graph retrieval."""

import logging
from typing import Any, Optional

from app.kg.client import Neo4jClient

logger = logging.getLogger(__name__)


# 节点标签常量
PROJECT = "Project"
TOKEN = "Token"
PERSON = "Person"
INSTITUTION = "Institution"
CHAIN = "Chain"

# 关系类型常量
ISSUED = "ISSUED"
INVESTED = "INVESTED"
BELONGS_TO = "BELONGS_TO"
COLLABORATES_WITH = "COLLABORATES_WITH"
WORKS_AT = "WORKS_AT"
ADVISES = "ADVISES"
FOUNDED = "FOUNDED"


class GraphQuery:
    """Query functions for the Neo4j knowledge graph."""

    def __init__(self, client: Neo4jClient) -> None:
        """Initialize the query service.

        Args:
            client: Neo4j client instance
        """
        self.client = client

    async def get_project_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """Get a project by name.

        Args:
            name: Project name

        Returns:
            Project node data or None
        """
        query = f"""
        MATCH (p:{PROJECT} {{name: $name}})
        RETURN p
        """
        result = await self.client.execute_query(query, {"name": name})
        return result[0]["p"] if result else None

    async def get_project_tokens(self, project_name: str) -> list[dict[str, Any]]:
        """Get all tokens issued by a project.

        Args:
            project_name: Project name

        Returns:
            List of token nodes
        """
        query = f"""
        MATCH (p:{PROJECT} {{name: $project_name}})<-[:{ISSUED}]-(t:{TOKEN})
        RETURN t
        """
        result = await self.client.execute_query(query, {"project_name": project_name})
        return [r["t"] for r in result]

    async def get_project_team(self, project_name: str) -> list[dict[str, Any]]:
        """Get all team members of a project.

        Args:
            project_name: Project name

        Returns:
            List of person nodes with their roles
        """
        query = f"""
        MATCH (p:{PROJECT} {{name: $project_name}})<-[r]-(person:{PERSON})
        RETURN person, type(r) as relationship, r.role as role
        """
        result = await self.client.execute_query(query, {"project_name": project_name})
        return [
            {
                "person": r["person"],
                "relationship": r["relationship"],
                "role": r.get("role"),
            }
            for r in result
        ]

    async def get_project_investors(self, project_name: str) -> list[dict[str, Any]]:
        """Get all investors of a project.

        Args:
            project_name: Project name

        Returns:
            List of institution nodes with investment details
        """
        query = f"""
        MATCH (p:{PROJECT} {{name: $project_name}})<-[r:{INVESTED}]-(i:{INSTITUTION})
        RETURN i, r.round_type as round_type, r.amount as amount
        """
        result = await self.client.execute_query(query, {"project_name": project_name})
        return [
            {
                "institution": r["i"],
                "round_type": r.get("round_type"),
                "amount": r.get("amount"),
            }
            for r in result
        ]

    async def get_project_chain(self, project_name: str) -> Optional[dict[str, Any]]:
        """Get the chain a project belongs to.

        Args:
            project_name: Project name

        Returns:
            Chain node or None
        """
        query = f"""
        MATCH (p:{PROJECT} {{name: $project_name}})-[:{BELONGS_TO}]->(c:{CHAIN})
        RETURN c
        """
        result = await self.client.execute_query(query, {"project_name": project_name})
        return result[0]["c"] if result else None

    async def get_institution_portfolio(self, institution_name: str) -> list[dict[str, Any]]:
        """Get all projects invested in by an institution.

        Args:
            institution_name: Institution name

        Returns:
            List of project nodes with investment details
        """
        query = f"""
        MATCH (i:{INSTITUTION} {{name: $institution_name}})-[:{INVESTED}]->(p:{PROJECT})
        RETURN p
        """
        result = await self.client.execute_query(query, {"institution_name": institution_name})
        return [r["p"] for r in result]

    async def get_person_projects(self, person_name: str) -> list[dict[str, Any]]:
        """Get all projects associated with a person.

        Args:
            person_name: Person name

        Returns:
            List of project nodes with relationship details
        """
        query = f"""
        MATCH (p:{PERSON} {{name: $person_name}})-[r]->(pr:{PROJECT})
        RETURN pr, type(r) as relationship, r.role as role
        """
        result = await self.client.execute_query(query, {"person_name": person_name})
        return [
            {
                "project": r["pr"],
                "relationship": r["relationship"],
                "role": r.get("role"),
            }
            for r in result
        ]

    async def get_chain_projects(self, chain_name: str) -> list[dict[str, Any]]:
        """Get all projects on a chain.

        Args:
            chain_name: Chain name

        Returns:
            List of project nodes
        """
        query = f"""
        MATCH (c:{CHAIN} {{name: $chain_name}})<-[:{BELONGS_TO}]-(p:{PROJECT})
        RETURN p
        """
        result = await self.client.execute_query(query, {"chain_name": chain_name})
        return [r["p"] for r in result]

    async def get_project_collaborations(self, project_name: str) -> list[dict[str, Any]]:
        """Get all projects that collaborate with a given project.

        Args:
            project_name: Project name

        Returns:
            List of collaborating project nodes
        """
        query = f"""
        MATCH (p:{PROJECT} {{name: $project_name}})-[:{COLLABORATES_WITH}]-(collab:{PROJECT})
        RETURN collab
        """
        result = await self.client.execute_query(query, {"project_name": project_name})
        return [r["collab"] for r in result]

    async def search_projects_by_keyword(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search projects by keyword in name or description.

        Args:
            keyword: Search keyword
            limit: Maximum results

        Returns:
            List of matching project nodes
        """
        query = f"""
        MATCH (p:{PROJECT})
        WHERE p.name CONTAINS $keyword OR p.description CONTAINS $keyword
        RETURN p
        LIMIT $limit
        """
        result = await self.client.execute_query(
            query,
            {"keyword": keyword, "limit": limit},
        )
        return [r["p"] for r in result]

    async def get_project_context(self, project_name: str) -> dict[str, Any]:
        """Get full context for a project including all related entities.

        Args:
            project_name: Project name

        Returns:
            Dictionary with project, tokens, team, investors, chain, collaborations
        """
        project = await self.get_project_by_name(project_name)
        if not project:
            return {}

        tokens = await self.get_project_tokens(project_name)
        team = await self.get_project_team(project_name)
        investors = await self.get_project_investors(project_name)
        chain = await self.get_project_chain(project_name)
        collaborations = await self.get_project_collaborations(project_name)

        return {
            "project": project,
            "tokens": tokens,
            "team": team,
            "investors": investors,
            "chain": chain,
            "collaborations": collaborations,
        }

    async def find_related_projects(
        self,
        project_name: str,
        max_hops: int = 2,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find projects related through investors, team, or collaborations.

        Args:
            project_name: Starting project name
            max_hops: Maximum relationship hops
            limit: Maximum results

        Returns:
            List of related project nodes with path information
        """
        query = f"""
        MATCH path = (p:{PROJECT} {{name: $project_name}})-[*1..{max_hops}]-(related:{PROJECT})
        WHERE related.name <> $project_name
        RETURN related, [node in nodes(path) | node.name] as path, length(path) as distance
        ORDER BY distance, related.name
        LIMIT $limit
        """
        result = await self.client.execute_query(
            query,
            {"project_name": project_name, "limit": limit},
        )
        return [
            {
                "project": r["related"],
                "path": r["path"],
                "distance": r["distance"],
            }
            for r in result
        ]

    async def get_graph_stats(self) -> dict[str, int]:
        """Get statistics about the knowledge graph.

        Returns:
            Dictionary with counts of each node type
        """
        stats = {}

        for node_type in [PROJECT, TOKEN, PERSON, INSTITUTION, CHAIN]:
            query = f"""
            MATCH (n:{node_type})
            RETURN count(n) as count
            """
            result = await self.client.execute_query(query)
            stats[node_type.lower() + "_count"] = result[0]["count"] if result else 0

        return stats

    async def get_token_info(self, symbol: str) -> Optional[dict[str, Any]]:
        """Get token information with associated project.

        Args:
            symbol: Token symbol

        Returns:
            Token node with project information or None
        """
        query = f"""
        MATCH (t:{TOKEN} {{symbol: $symbol}})-[:{ISSUED}]->(p:{PROJECT})
        RETURN t, p
        """
        result = await self.client.execute_query(query, {"symbol": symbol})
        if result:
            return {
                "token": result[0]["t"],
                "project": result[0]["p"],
            }
        return None

    async def batch_get_projects_context(
        self,
        project_names: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Get context for multiple projects efficiently.

        Args:
            project_names: List of project names

        Returns:
            Dictionary mapping project names to their context
        """
        contexts = {}
        for name in project_names:
            contexts[name] = await self.get_project_context(name)
        return contexts
