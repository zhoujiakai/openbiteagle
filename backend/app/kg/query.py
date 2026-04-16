"""知识图谱检索的图查询函数。"""

from typing import Any, Optional

from app.data.logger import create_logger
from app.kg.client import Neo4jClient
from app.kg.models import NodeTypes, RelationTypes

logger = create_logger("知识图谱查询")

# 节点标签简写，方便 Cypher 查询拼接
N = NodeTypes
R = RelationTypes


class GraphQuery:
    """Neo4j 知识图谱的查询函数。"""

    def __init__(self, client: Neo4jClient) -> None:
        """初始化查询服务。

        Args:
            client: Neo4j 客户端实例
        """
        self.client = client

    async def get_project_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """根据名称获取项目。

        Args:
            name: 项目名称

        Returns:
            项目节点数据或 None
        """
        query = f"""
        MATCH (p:{N.PROJECT.value} {{name: $name}})
        RETURN p
        """
        result = await self.client.execute_query(query, {"name": name})
        return result[0]["p"] if result else None

    async def get_project_tokens(self, project_name: str) -> list[dict[str, Any]]:
        """获取项目发行的所有代币。

        Args:
            project_name: 项目名称

        Returns:
            代币节点列表
        """
        query = f"""
        MATCH (p:{N.PROJECT.value} {{name: $project_name}})<-[:{R.ISSUED.value}]-(t:{N.TOKEN.value})
        RETURN t
        """
        result = await self.client.execute_query(query, {"project_name": project_name})
        return [r["t"] for r in result]

    async def get_project_team(self, project_name: str) -> list[dict[str, Any]]:
        """获取项目的所有团队成员。

        Args:
            project_name: 项目名称

        Returns:
            包含角色信息的人物节点列表
        """
        query = f"""
        MATCH (p:{N.PROJECT.value} {{name: $project_name}})<-[r]-(person:{N.PERSON.value})
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
        """获取项目的所有投资方。

        Args:
            project_name: 项目名称

        Returns:
            包含投资详情的机构节点列表
        """
        query = f"""
        MATCH (p:{N.PROJECT.value} {{name: $project_name}})<-[r:{R.INVESTED.value}]-(i:{N.INSTITUTION.value})
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
        """获取项目所属的公链。

        Args:
            project_name: 项目名称

        Returns:
            公链节点或 None
        """
        query = f"""
        MATCH (p:{N.PROJECT.value} {{name: $project_name}})-[:{R.BELONGS_TO.value}]->(c:{N.CHAIN.value})
        RETURN c
        """
        result = await self.client.execute_query(query, {"project_name": project_name})
        return result[0]["c"] if result else None

    async def get_institution_portfolio(self, institution_name: str) -> list[dict[str, Any]]:
        """获取机构投资的所有项目。

        Args:
            institution_name: 机构名称

        Returns:
            包含投资详情的项目节点列表
        """
        query = f"""
        MATCH (i:{N.INSTITUTION.value} {{name: $institution_name}})-[:{R.INVESTED.value}]->(p:{N.PROJECT.value})
        RETURN p
        """
        result = await self.client.execute_query(query, {"institution_name": institution_name})
        return [r["p"] for r in result]

    async def get_person_projects(self, person_name: str) -> list[dict[str, Any]]:
        """获取与某人物关联的所有项目。

        Args:
            person_name: 人物名称

        Returns:
            包含关系详情的项目节点列表
        """
        query = f"""
        MATCH (p:{N.PERSON.value} {{name: $person_name}})-[r]->(pr:{N.PROJECT.value})
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
        """获取公链上的所有项目。

        Args:
            chain_name: 公链名称

        Returns:
            项目节点列表
        """
        query = f"""
        MATCH (c:{N.CHAIN.value} {{name: $chain_name}})<-[:{R.BELONGS_TO.value}]-(p:{N.PROJECT.value})
        RETURN p
        """
        result = await self.client.execute_query(query, {"chain_name": chain_name})
        return [r["p"] for r in result]

    async def get_project_collaborations(self, project_name: str) -> list[dict[str, Any]]:
        """获取与指定项目合作的所有项目。

        Args:
            project_name: 项目名称

        Returns:
            合作项目节点列表
        """
        query = f"""
        MATCH (p:{N.PROJECT.value} {{name: $project_name}})-[:{R.COLLABORATES_WITH.value}]-(collab:{N.PROJECT.value})
        RETURN collab
        """
        result = await self.client.execute_query(query, {"project_name": project_name})
        return [r["collab"] for r in result]

    async def search_projects_by_keyword(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        """按关键词在名称或描述中搜索项目。

        Args:
            keyword: 搜索关键词
            limit: 最大结果数

        Returns:
            匹配的项目节点列表
        """
        query = f"""
        MATCH (p:{N.PROJECT.value})
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
        """获取项目的完整上下文，包括所有相关实体。

        Args:
            project_name: 项目名称

        Returns:
            包含项目、代币、团队、投资方、公链、合作的字典
        """
        project = await self.get_project_by_name(project_name)
        if not project:
            return {}

        tokens = await self.get_project_tokens(project_name)
        team = await self.get_project_team(project_name)
        investors = await self.get_project_investors(project_name)
        chain = await self.get_project_chain(project_name)

        return {
            "project": project,
            "tokens": tokens,
            "team": team,
            "investors": investors,
            "chain": chain,
        }

    async def find_related_projects(
        self,
        project_name: str,
        max_hops: int = 2,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """查找通过投资方、团队或合作关联的项目。

        Args:
            project_name: 起始项目名称
            max_hops: 最大关系跳数
            limit: 最大结果数

        Returns:
            包含路径信息的关联项目节点列表
        """
        query = f"""
        MATCH path = (p:{N.PROJECT.value} {{name: $project_name}})-[*1..{max_hops}]-(related:{N.PROJECT.value})
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
        """获取知识图谱的统计信息。

        Returns:
            包含各节点类型数量的字典
        """
        stats = {}

        for node_type in N:
            query = f"""
            MATCH (n:{node_type.value})
            RETURN count(n) as count
            """
            result = await self.client.execute_query(query)
            stats[node_type.value.lower() + "_count"] = result[0]["count"] if result else 0

        return stats

    async def get_token_info(self, symbol: str) -> Optional[dict[str, Any]]:
        """获取代币信息及其关联项目。

        Args:
            symbol: 代币符号

        Returns:
            包含项目信息的代币节点或 None
        """
        query = f"""
        MATCH (t:{N.TOKEN.value} {{symbol: $symbol}})-[:{R.ISSUED.value}]->(p:{N.PROJECT.value})
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
        """高效获取多个项目的上下文。

        Args:
            project_names: 项目名称列表

        Returns:
            项目名称到其上下文的映射字典
        """
        contexts = {}
        for name in project_names:
            contexts[name] = await self.get_project_context(name)
        return contexts
