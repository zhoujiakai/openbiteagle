"""Rootdata to Neo4j Knowledge Graph importer.

This module handles converting Rootdata ProjectInfo objects into
Neo4j graph nodes and relationships.
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
    """Normalize chain name to a standard format.

    Args:
        name: Raw chain name from Rootdata

    Returns:
        Normalized chain name
    """
    # 检查直接映射
    if name in CHAIN_ALIASES:
        return CHAIN_ALIASES[name]

    # 首字母大写
    return name.capitalize()


class RootdataKGImporter:
    """Import Rootdata projects into Neo4j Knowledge Graph."""

    def __init__(self, loader: GraphLoader):
        """Initialize the importer.

        Args:
            loader: GraphLoader instance for Neo4j operations
        """
        self.loader = loader

    def project_to_node(self, project: ProjectInfo) -> ProjectNode:
        """Convert ProjectInfo to ProjectNode.

        Args:
            project: Rootdata ProjectInfo

        Returns:
            ProjectNode for KG
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
        """Convert ProjectInfo token to TokenNode.

        Args:
            project: Rootdata ProjectInfo

        Returns:
            TokenNode or None if no token
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
        """Convert project chains to ChainNodes.

        Args:
            project: Rootdata ProjectInfo

        Returns:
            List of ChainNodes
        """
        chains = set()
        for chain_name in project.chains:
            normalized = normalize_chain_name(chain_name)
            if normalized:
                chains.add(normalized)

        return [ChainNode(name=name) for name in sorted(chains)]

    def investors_to_nodes(self, project: ProjectInfo) -> list[InstitutionNode]:
        """Convert project investors to InstitutionNodes.

        Args:
            project: Rootdata ProjectInfo

        Returns:
            List of InstitutionNodes
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
        """Import a single Rootdata project into the Knowledge Graph.

        Args:
            project: Rootdata ProjectInfo

        Returns:
            Dict with import results
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
        """Import multiple Rootdata projects into the Knowledge Graph.

        Args:
            projects: List of Rootdata ProjectInfo objects
            skip_existing: Skip projects that already exist (by rootdata_id)

        Returns:
            Dict with batch import statistics
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
    """Convenience function to import Rootdata projects to Neo4j KG.

    Args:
        client: Neo4jClient instance
        projects: List of ProjectInfo objects
        skip_existing: Skip projects that already exist

    Returns:
        Import statistics dict
    """
    loader = GraphLoader(client)

    # 初始化约束
    await loader.create_constraints()

    # 导入项目
    importer = RootdataKGImporter(loader)
    return await importer.import_batch(projects, skip_existing=skip_existing)
