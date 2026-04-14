"""Graph data loader for building the knowledge graph."""

import logging
from typing import Any, Optional

from app.kg.client import Neo4jClient
from app.kg.models import (
    ChainNode,
    InstitutionNode,
    PersonNode,
    ProjectNode,
    RelationTypes,
    TokenNode,
)

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


class GraphLoader:
    """Load data into the Neo4j knowledge graph."""

    def __init__(self, client: Neo4jClient) -> None:
        """Initialize the loader.

        Args:
            client: Neo4j client instance
        """
        self.client = client

    async def create_constraints(self) -> None:
        """Create unique constraints for node labels."""
        constraints = [
            # 项目唯一性约束
            f"CREATE CONSTRAINT project_name IF NOT EXISTS FOR (p:{PROJECT}) REQUIRE p.name IS UNIQUE",

            # 代币唯一性约束
            f"CREATE CONSTRAINT token_symbol IF NOT EXISTS FOR (t:{TOKEN}) REQUIRE t.symbol IS UNIQUE",
            f"CREATE CONSTRAINT token_address IF NOT EXISTS FOR (t:{TOKEN}) REQUIRE t.contract_address IS UNIQUE",

            # 人物唯一性约束
            f"CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:{PERSON}) REQUIRE p.name IS UNIQUE",

            # 机构唯一性约束
            f"CREATE CONSTRAINT institution_name IF NOT EXISTS FOR (i:{INSTITUTION}) REQUIRE i.name IS UNIQUE",

            # 公链唯一性约束
            f"CREATE CONSTRAINT chain_name IF NOT EXISTS FOR (c:{CHAIN}) REQUIRE c.name IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                await self.client.execute_write(constraint)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning(f"Constraint creation warning: {e}")

        logger.info("Graph constraints created/verified")

    async def create_project(self, project: ProjectNode) -> dict[str, Any]:
        """Create a Project node.

        Args:
            project: Project node data

        Returns:
            Created node data
        """
        query = f"""
        MERGE (p:{PROJECT} {{name: $name}})
        SET p += $props
        RETURN p
        """
        result = await self.client.execute_query(
            query,
            {"name": project.name, "props": project.to_dict()},
        )
        return result[0]["p"] if result else {}

    async def create_token(self, token: TokenNode) -> dict[str, Any]:
        """Create a Token node.

        Args:
            token: Token node data

        Returns:
            Created node data
        """
        query = f"""
        MERGE (t:{TOKEN} {{symbol: $symbol}})
        SET t += $props
        RETURN t
        """
        result = await self.client.execute_query(
            query,
            {"symbol": token.symbol, "props": token.to_dict()},
        )
        return result[0]["t"] if result else {}

    async def create_person(self, person: PersonNode) -> dict[str, Any]:
        """Create a Person node.

        Args:
            person: Person node data

        Returns:
            Created node data
        """
        query = f"""
        MERGE (p:{PERSON} {{name: $name}})
        SET p += $props
        RETURN p
        """
        result = await self.client.execute_query(
            query,
            {"name": person.name, "props": person.to_dict()},
        )
        return result[0]["p"] if result else {}

    async def create_institution(self, institution: InstitutionNode) -> dict[str, Any]:
        """Create an Institution node.

        Args:
            institution: Institution node data

        Returns:
            Created node data
        """
        query = f"""
        MERGE (i:{INSTITUTION} {{name: $name}})
        SET i += $props
        RETURN i
        """
        result = await self.client.execute_query(
            query,
            {"name": institution.name, "props": institution.to_dict()},
        )
        return result[0]["i"] if result else {}

    async def create_chain(self, chain: ChainNode) -> dict[str, Any]:
        """Create a Chain node.

        Args:
            chain: Chain node data

        Returns:
            Created node data
        """
        query = f"""
        MERGE (c:{CHAIN} {{name: $name}})
        SET c += $props
        RETURN c
        """
        result = await self.client.execute_query(
            query,
            {"name": chain.name, "props": chain.to_dict()},
        )
        return result[0]["c"] if result else {}

    async def relate_token_to_project(
        self,
        token_symbol: str,
        project_name: str,
    ) -> None:
        """Create ISSUED relationship: Token -[ISSUED]-> Project.

        Args:
            token_symbol: Token symbol
            project_name: Project name
        """
        query = f"""
        MATCH (t:{TOKEN} {{symbol: $token_symbol}})
        MATCH (p:{PROJECT} {{name: $project_name}})
        MERGE (t)-[:{ISSUED}]->(p)
        """
        await self.client.execute_write(
            query,
            {"token_symbol": token_symbol, "project_name": project_name},
        )

    async def relate_institution_to_project(
        self,
        institution_name: str,
        project_name: str,
        round_type: Optional[str] = None,
        amount: Optional[str] = None,
    ) -> None:
        """Create INVESTED relationship: Institution -[INVESTED]-> Project.

        Args:
            institution_name: Institution name
            project_name: Project name
            round_type: Optional investment round type (e.g., "Series A")
            amount: Optional investment amount
        """
        props = {}
        if round_type:
            props["round_type"] = round_type
        if amount:
            props["amount"] = amount

        query = f"""
        MATCH (i:{INSTITUTION} {{name: $institution_name}})
        MATCH (p:{PROJECT} {{name: $project_name}})
        MERGE (i)-[r:{INVESTED}]->(p)
        """
        params = {"institution_name": institution_name, "project_name": project_name, **props}

        if props:
            query += " SET r += $props"
            params = {"institution_name": institution_name, "project_name": project_name, "props": props}

        await self.client.execute_write(query, params)

    async def relate_project_to_chain(
        self,
        project_name: str,
        chain_name: str,
    ) -> None:
        """Create BELONGS_TO relationship: Project -[BELONGS_TO]-> Chain.

        Args:
            project_name: Project name
            chain_name: Chain name
        """
        query = f"""
        MATCH (p:{PROJECT} {{name: $project_name}})
        MATCH (c:{CHAIN} {{name: $chain_name}})
        MERGE (p)-[:{BELONGS_TO}]->(c)
        """
        await self.client.execute_write(
            query,
            {"project_name": project_name, "chain_name": chain_name},
        )

    async def relate_person_to_project(
        self,
        person_name: str,
        project_name: str,
        relation_type: RelationTypes | str = RelationTypes.WORKS_AT,
        role: Optional[str] = None,
    ) -> None:
        """Create relationship: Person -[relation_type]-> Project.

        Args:
            person_name: Person name
            project_name: Project name
            relation_type: Type of relationship (WORKS_AT, ADVISES, FOUNDED)
            role: Optional role description
        """
        # 如果需要，将枚举转换为字符串
        if hasattr(relation_type, "value"):
            relation_type = relation_type.value

        rel_props = ""
        params = {"person_name": person_name, "project_name": project_name}

        if role:
            rel_props = " {{role: $role}}"
            params["role"] = role

        query = f"""
        MATCH (p:{PERSON} {{name: $person_name}})
        MATCH (pr:{PROJECT} {{name: $project_name}})
        MERGE (p)-[r:{relation_type}{rel_props}]->(pr)
        """
        await self.client.execute_write(query, params)

    async def relate_projects(
        self,
        project_a: str,
        project_b: str,
        collaboration_type: Optional[str] = None,
    ) -> None:
        """Create COLLABORATES_WITH relationship: Project -[COLLABORATES_WITH]-> Project.

        Args:
            project_a: First project name
            project_b: Second project name
            collaboration_type: Optional description of collaboration
        """
        rel_props = ""
        params = {"project_a": project_a, "project_b": project_b}

        if collaboration_type:
            rel_props = " {{type: $collab_type}}"
            params["collab_type"] = collaboration_type

        query = f"""
        MATCH (p1:{PROJECT} {{name: $project_a}})
        MATCH (p2:{PROJECT} {{name: $project_b}})
        MERGE (p1)-[r:{COLLABORATES_WITH}{rel_props}]->(p2)
        """
        await self.client.execute_write(query, params)

    async def create_full_project(
        self,
        project: ProjectNode,
        chain: Optional[str] = None,
        tokens: Optional[list[TokenNode]] = None,
        team: Optional[list[tuple[PersonNode, RelationTypes]]] = None,
        investors: Optional[list[tuple[InstitutionNode, str | None, str | None]]] = None,
    ) -> None:
        """Create a project with all its relationships.

        Args:
            project: Project node data
            chain: Optional chain name
            tokens: Optional list of tokens
            team: Optional list of (person, relation_type) tuples
            investors: Optional list of (institution, round_type, amount) tuples
        """
        # 创建项目
        await self.create_project(project)

        # 创建公链关系
        if chain:
            await self.create_chain(ChainNode(name=chain))
            await self.relate_project_to_chain(project.name, chain)

        # 创建代币
        if tokens:
            for token in tokens:
                await self.create_token(token)
                await self.relate_token_to_project(token.symbol, project.name)

        # 创建团队关系
        if team:
            for person, relation_type in team:
                await self.create_person(person)
                await self.relate_person_to_project(person.name, project.name, relation_type)

        # 创建投资方关系
        if investors:
            for institution, round_type, amount in investors:
                await self.create_institution(institution)
                await self.relate_institution_to_project(
                    institution.name,
                    project.name,
                    round_type,
                    amount,
                )

        logger.info(f"Created full project: {project.name}")
