"""用于构建知识图谱的图数据加载器。"""

from typing import Any, Optional

from app.data.logger import create_logger
from app.kg.client import Neo4jClient
from app.kg.models import (
    ChainNode,
    InstitutionNode,
    NodeTypes,
    PersonNode,
    ProjectNode,
    RelationTypes,
    TokenNode,
)

logger = create_logger("知识图谱加载器")

# 节点标签简写，方便 Cypher 查询拼接
N = NodeTypes
R = RelationTypes


class GraphLoader:
    """将数据加载到 Neo4j 知识图谱。"""

    def __init__(self, client: Neo4jClient) -> None:
        """初始化加载器。

        Args:
            client: Neo4j 客户端实例
        """
        self.client = client

    async def create_constraints(self) -> None:
        """为节点标签创建唯一约束。"""
        constraints = [
            # 项目唯一性约束
            f"CREATE CONSTRAINT project_name IF NOT EXISTS FOR (p:{N.PROJECT.value}) REQUIRE p.name IS UNIQUE",

            # 代币唯一性约束
            f"CREATE CONSTRAINT token_symbol IF NOT EXISTS FOR (t:{N.TOKEN.value}) REQUIRE t.symbol IS UNIQUE",
            f"CREATE CONSTRAINT token_address IF NOT EXISTS FOR (t:{N.TOKEN.value}) REQUIRE t.contract_address IS UNIQUE",

            # 人物唯一性约束
            f"CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:{N.PERSON.value}) REQUIRE p.name IS UNIQUE",

            # 机构唯一性约束
            f"CREATE CONSTRAINT institution_name IF NOT EXISTS FOR (i:{N.INSTITUTION.value}) REQUIRE i.name IS UNIQUE",

            # 公链唯一性约束
            f"CREATE CONSTRAINT chain_name IF NOT EXISTS FOR (c:{N.CHAIN.value}) REQUIRE c.name IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                await self.client.execute_write(constraint)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning(f"Constraint creation warning: {e}")

        logger.info("Graph constraints created/verified")

    async def create_project(self, project: ProjectNode) -> dict[str, Any]:
        """创建项目节点。

        Args:
            project: 项目节点数据

        Returns:
            创建的节点数据
        """
        query = f"""
        MERGE (p:{N.PROJECT.value} {{name: $name}})
        SET p += $props
        RETURN p
        """
        result = await self.client.execute_query(
            query,
            {"name": project.name, "props": project.to_dict()},
        )
        return result[0]["p"] if result else {}

    async def create_token(self, token: TokenNode) -> dict[str, Any]:
        """创建代币节点。

        Args:
            token: 代币节点数据

        Returns:
            创建的节点数据
        """
        query = f"""
        MERGE (t:{N.TOKEN.value} {{symbol: $symbol}})
        SET t += $props
        RETURN t
        """
        result = await self.client.execute_query(
            query,
            {"symbol": token.symbol, "props": token.to_dict()},
        )
        return result[0]["t"] if result else {}

    async def create_person(self, person: PersonNode) -> dict[str, Any]:
        """创建人物节点。

        Args:
            person: 人物节点数据

        Returns:
            创建的节点数据
        """
        query = f"""
        MERGE (p:{N.PERSON.value} {{name: $name}})
        SET p += $props
        RETURN p
        """
        result = await self.client.execute_query(
            query,
            {"name": person.name, "props": person.to_dict()},
        )
        return result[0]["p"] if result else {}

    async def create_institution(self, institution: InstitutionNode) -> dict[str, Any]:
        """创建机构节点。

        Args:
            institution: 机构节点数据

        Returns:
            创建的节点数据
        """
        query = f"""
        MERGE (i:{N.INSTITUTION.value} {{name: $name}})
        SET i += $props
        RETURN i
        """
        result = await self.client.execute_query(
            query,
            {"name": institution.name, "props": institution.to_dict()},
        )
        return result[0]["i"] if result else {}

    async def create_chain(self, chain: ChainNode) -> dict[str, Any]:
        """创建公链节点。

        Args:
            chain: 公链节点数据

        Returns:
            创建的节点数据
        """
        query = f"""
        MERGE (c:{N.CHAIN.value} {{name: $name}})
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
        """创建 ISSUED 关系：Token -[ISSUED]-> Project。

        Args:
            token_symbol: 代币符号
            project_name: 项目名称
        """
        query = f"""
        MATCH (t:{N.TOKEN.value} {{symbol: $token_symbol}})
        MATCH (p:{N.PROJECT.value} {{name: $project_name}})
        MERGE (t)-[:{R.ISSUED.value}]->(p)
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
        """创建 INVESTED 关系：Institution -[INVESTED]-> Project。

        Args:
            institution_name: 机构名称
            project_name: 项目名称
            round_type: 可选的投资轮次类型（例如 "Series A"）
            amount: 可选的投资金额
        """
        props = {}
        if round_type:
            props["round_type"] = round_type
        if amount:
            props["amount"] = amount

        query = f"""
        MATCH (i:{N.INSTITUTION.value} {{name: $institution_name}})
        MATCH (p:{N.PROJECT.value} {{name: $project_name}})
        MERGE (i)-[r:{R.INVESTED.value}]->(p)
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
        """创建 BELONGS_TO 关系：Project -[BELONGS_TO]-> Chain。

        Args:
            project_name: 项目名称
            chain_name: 公链名称
        """
        query = f"""
        MATCH (p:{N.PROJECT.value} {{name: $project_name}})
        MATCH (c:{N.CHAIN.value} {{name: $chain_name}})
        MERGE (p)-[:{R.BELONGS_TO.value}]->(c)
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
        """创建关系：Person -[relation_type]-> Project。

        Args:
            person_name: 人物名称
            project_name: 项目名称
            relation_type: 关系类型（WORKS_AT、ADVISES、FOUNDED）
            role: 可选的角色描述
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
        MATCH (p:{N.PERSON.value} {{name: $person_name}})
        MATCH (pr:{N.PROJECT.value} {{name: $project_name}})
        MERGE (p)-[r:{relation_type}{rel_props}]->(pr)
        """
        await self.client.execute_write(query, params)

    async def relate_projects(
        self,
        project_a: str,
        project_b: str,
        collaboration_type: Optional[str] = None,
    ) -> None:
        """创建 COLLABORATES_WITH 关系：Project -[COLLABORATES_WITH]-> Project。

        Args:
            project_a: 第一个项目名称
            project_b: 第二个项目名称
            collaboration_type: 可选的合作描述
        """
        rel_props = ""
        params = {"project_a": project_a, "project_b": project_b}

        if collaboration_type:
            rel_props = " {{type: $collab_type}}"
            params["collab_type"] = collaboration_type

        query = f"""
        MATCH (p1:{N.PROJECT.value} {{name: $project_a}})
        MATCH (p2:{N.PROJECT.value} {{name: $project_b}})
        MERGE (p1)-[r:{R.COLLABORATES_WITH.value}{rel_props}]->(p2)
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
        """创建项目及其所有关系。

        Args:
            project: 项目节点数据
            chain: 可选的公链名称
            tokens: 可选的代币列表
            team: 可选的 (人物, 关系类型) 元组列表
            investors: 可选的 (机构, 轮次类型, 金额) 元组列表
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
