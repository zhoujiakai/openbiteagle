"""Rootdata 到 Neo4j 知识图谱的导入器。

该模块负责将 Rootdata 的 ProjectInfo 对象转换为
Neo4j 图节点和关系。
"""

import logging
from typing import Optional

from app.kg.client import Neo4jClient
from app.kg.loader import GraphLoader
from app.kg.models import (
    ChainNode,
    InstitutionNode,
    ProjectNode,
    TokenNode,
)
from app.wrappers.rootdata.models import ProjectInfo

logger = logging.getLogger(__name__)


# 常见公链名称映射，用于标准化名称
CHAIN_ALIASES = {
    "ETH": "Ethereum",
    "Ethereum": "Ethereum",
    "BSC": "Binance Smart Chain",
    "BSC Chain": "Binance Smart Chain",
    "Solana": "Solana",
    "SOL": "Solana",
    "Polygon": "Polygon",
    "MATIC": "Polygon",
    "Arbitrum": "Arbitrum",
    "ARB": "Arbitrum",
    "Optimism": "Optimism",
    "OP": "Optimism",
    "Avalanche": "Avalanche",
    "AVAX": "Avalanche",
    "Fantom": "Fantom",
    "FTM": "Fantom",
    "Aptos": "Aptos",
    "APT": "Aptos",
    "Cosmos": "Cosmos",
    "ATOM": "Cosmos",
    "Near": "NEAR",
    "Sui": "Sui",
    "SUI": "Sui",
}


def normalize_chain_name(name: str) -> str:
    """将公链名称标准化为统一格式。

    Args:
        name: 来自 Rootdata 的原始公链名称

    Returns:
        标准化后的公链名称
    """
    # 检查直接映射
    if name in CHAIN_ALIASES:
        return CHAIN_ALIASES[name]

    # 首字母大写
    return name.capitalize()


class RootdataKGImporter:
    """将 Rootdata 项目导入 Neo4j 知识图谱。"""

    def __init__(self, loader: GraphLoader):
        """初始化导入器。

        Args:
            loader: 用于 Neo4j 操作的 GraphLoader 实例
        """
        self.loader = loader

    def project_to_node(self, project: ProjectInfo) -> ProjectNode:
        """将 ProjectInfo 转换为 ProjectNode。

        Args:
            project: Rootdata 的 ProjectInfo

        Returns:
            知识图谱的 ProjectNode
        """
        return ProjectNode(
            name=project.name,
            description=project.introduction or project.description,
            website=project.website_url,
            twitter=project.twitter,
            discord=project.discord,
            telegram=project.telegram,
            rootdata_id=project.rootdata_id,
            logo_url=project.logo_url,
        )

    def token_to_node(self, project: ProjectInfo) -> Optional[TokenNode]:
        """将 ProjectInfo 代币转换为 TokenNode。

        Args:
            project: Rootdata 的 ProjectInfo

        Returns:
            TokenNode，如果没有代币则返回 None
        """
        if not project.token:
            return None

        # 如果有公链信息，使用第一条
        chain = None
        if project.chains:
            chain = normalize_chain_name(project.chains[0])

        return TokenNode(
            symbol=project.token.symbol,
            name=project.token.name,
            contract_address=project.token.contract_address,
            chain=chain,
        )

    def chains_to_nodes(self, project: ProjectInfo) -> list[ChainNode]:
        """将项目公链转换为 ChainNodes。

        Args:
            project: Rootdata 的 ProjectInfo

        Returns:
            ChainNode 列表
        """
        chains = set()
        for chain_name in project.chains:
            normalized = normalize_chain_name(chain_name)
            if normalized:
                chains.add(normalized)

        return [ChainNode(name=name) for name in sorted(chains)]

    def investors_to_nodes(self, project: ProjectInfo) -> list[InstitutionNode]:
        """将项目投资方转换为 InstitutionNodes。

        Args:
            project: Rootdata 的 ProjectInfo

        Returns:
            InstitutionNode 列表
        """
        institutions = []
        for investor_name in project.investors:
            if investor_name and investor_name.strip():
                institutions.append(
                    InstitutionNode(
                        name=investor_name.strip(),
                    )
                )
        return institutions

    async def import_project(self, project: ProjectInfo) -> dict:
        """将单个 Rootdata 项目导入知识图谱。

        Args:
            project: Rootdata 的 ProjectInfo

        Returns:
            包含导入结果的字典
        """
        result = {
            "project": project.name,
            "success": False,
            "nodes_created": [],
            "relationships_created": [],
        }

        try:
            # 转换为节点
            project_node = self.project_to_node(project)
            token_node = self.token_to_node(project)
            chain_nodes = self.chains_to_nodes(project)
            institution_nodes = self.investors_to_nodes(project)

            # 创建项目
            await self.loader.create_project(project_node)
            result["nodes_created"].append("Project")

            # 创建并关联代币
            if token_node:
                await self.loader.create_token(token_node)
                await self.loader.relate_token_to_project(
                    token_node.symbol, project_node.name
                )
                result["nodes_created"].append("Token")
                result["relationships_created"].append("ISSUED")

            # 创建并关联公链
            for chain_node in chain_nodes:
                await self.loader.create_chain(chain_node)
                await self.loader.relate_project_to_chain(project_node.name, chain_node.name)
            if chain_nodes:
                result["nodes_created"].append(f"{len(chain_nodes)} Chains")
                result["relationships_created"].append(f"{len(chain_nodes)} BELONGS_TO")

            # 创建并关联投资方
            for institution_node in institution_nodes:
                await self.loader.create_institution(institution_node)
                await self.loader.relate_institution_to_project(
                    institution_node.name, project_node.name
                )
            if institution_nodes:
                result["nodes_created"].append(f"{len(institution_nodes)} Institutions")
                result["relationships_created"].append(f"{len(institution_nodes)} INVESTED")

            result["success"] = True
            logger.info(f"Imported project to KG: {project.name}")

        except Exception as e:
            logger.error(f"Failed to import project {project.name}: {e}")
            result["error"] = str(e)

        return result

    async def import_batch(
        self,
        projects: list[ProjectInfo],
        skip_existing: bool = True,
    ) -> dict:
        """将多个 Rootdata 项目导入知识图谱。

        Args:
            projects: Rootdata ProjectInfo 对象列表
            skip_existing: 跳过已存在的项目（按 rootdata_id）

        Returns:
            包含批量导入统计信息的字典
        """
        stats = {
            "total": len(projects),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "nodes_created": 0,
            "relationships_created": 0,
            "errors": [],
        }

        for i, project in enumerate(projects):
            logger.info(f"Importing {i + 1}/{len(projects)}: {project.name}")

            # 检查是否已存在
            if skip_existing:
                # 可以在此添加检查，但目前通过 MERGE 操作处理重复数据
                pass

            try:
                result = await self.import_project(project)

                if result["success"]:
                    stats["success"] += 1
                    stats["nodes_created"] += len(result["nodes_created"])
                    stats["relationships_created"] += len(result["relationships_created"])
                else:
                    stats["failed"] += 1
                    if "error" in result:
                        stats["errors"].append({
                            "project": project.name,
                            "error": result["error"],
                        })

            except Exception as e:
                logger.error(f"Error importing {project.name}: {e}")
                stats["failed"] += 1
                stats["errors"].append({
                    "project": project.name,
                    "error": str(e),
                })

        return stats


async def import_rootdata_to_kg(
    client: Neo4jClient,
    projects: list[ProjectInfo],
    skip_existing: bool = True,
) -> dict:
    """导入 Rootdata 项目到 Neo4j 知识图谱的便捷函数。

    Args:
        client: Neo4jClient 实例
        projects: ProjectInfo 对象列表
        skip_existing: 跳过已存在的项目

    Returns:
        导入统计信息字典
    """
    loader = GraphLoader(client)

    # 初始化约束
    await loader.create_constraints()

    # 导入项目
    importer = RootdataKGImporter(loader)
    return await importer.import_batch(projects, skip_existing=skip_existing)
