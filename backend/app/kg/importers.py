"""Rootdata 到 Neo4j 知识图谱的导入器。

该模块负责将 Rootdata 的 ProjectInfo 对象转换为
Neo4j 图节点和关系。
"""

from typing import Optional

from app.data.logger import create_logger
from app.kg.client import Neo4jClient
from app.kg.loader import GraphLoader
from app.kg.models import (
    ChainNode,
    InstitutionNode,
    NodeTypes,
    PersonNode,
    PersonRole,
    ProjectNode,
    RelationTypes,
    TokenNode,
)
from app.wrappers.rootdata.models import FundingRound, ProjectInfo, TeamMember

logger = create_logger("知识图谱导入器")


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
            establishment_date=project.establishment_date,
            total_funding=project.total_funding,
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

        优先使用 investor_details（含 logo 等额外信息），
        回退到 investors（纯名称列表）。

        Args:
            project: Rootdata 的 ProjectInfo

        Returns:
            InstitutionNode 列表
        """
        institutions = []
        seen = set()

        # 优先使用 investor_details
        if project.investor_details:
            for inv in project.investor_details:
                name = inv.name.strip()
                if name and name not in seen:
                    seen.add(name)
                    institutions.append(InstitutionNode(name=name))
        else:
            # 回退到 investors 纯名称列表
            for investor_name in project.investors:
                name = investor_name.strip()
                if name and name not in seen:
                    seen.add(name)
                    institutions.append(InstitutionNode(name=name))

        return institutions

    def team_to_nodes(self, project: ProjectInfo) -> list[tuple[PersonNode, RelationTypes]]:
        """将 ProjectInfo.team_members 转换为 (PersonNode, 关系类型) 元组列表。

        根据 position 映射到 PersonRole 和 RelationTypes：
        - 包含 "founder" → FOUNDER + FOUNDED
        - 包含 "advisor" → ADVISOR + ADVISES
        - 其他 → TEAM_MEMBER + WORKS_AT

        Args:
            project: Rootdata 的 ProjectInfo

        Returns:
            (PersonNode, RelationTypes) 元组列表
        """
        result = []
        for member in project.team_members:
            position_lower = (member.position or "").lower()

            if "founder" in position_lower:
                role = PersonRole.FOUNDER
                relation = RelationTypes.FOUNDED
            elif "advisor" in position_lower:
                role = PersonRole.ADVISOR
                relation = RelationTypes.ADVISES
            else:
                role = PersonRole.TEAM_MEMBER
                relation = RelationTypes.WORKS_AT

            person = PersonNode(
                name=member.name,
                role=role,
                twitter=member.twitter,
                linkedin=member.linkedin,
            )
            result.append((person, relation))
        return result

    def funding_to_relations(
        self, project: ProjectInfo
    ) -> list[tuple[str, str, Optional[str], Optional[str]]]:
        """将 ProjectInfo.funding_details 转换为投资关系元组列表。

        Args:
            project: Rootdata 的 ProjectInfo

        Returns:
            (投资方名称, 项目名称, 轮次, 金额) 元组列表
        """
        result = []
        for fr in project.funding_details:
            round_type = fr.round_name
            amount_str = str(fr.amount) if fr.amount is not None else None
            for inv_name in fr.investors:
                if inv_name and inv_name.strip():
                    result.append((
                        inv_name.strip(),
                        project.name,
                        round_type,
                        amount_str,
                    ))
        return result

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
            result["nodes_created"].append(NodeTypes.PROJECT.value)

            # 创建并关联代币
            if token_node:
                await self.loader.create_token(token_node)
                await self.loader.relate_token_to_project(
                    token_node.symbol, project_node.name
                )
                result["nodes_created"].append(NodeTypes.TOKEN.value)
                result["relationships_created"].append(RelationTypes.ISSUED.value)

            # 创建并关联公链
            for chain_node in chain_nodes:
                await self.loader.create_chain(chain_node)
                await self.loader.relate_project_to_chain(project_node.name, chain_node.name)
            if chain_nodes:
                result["nodes_created"].append(f"{len(chain_nodes)} Chains")
                result["relationships_created"].append(f"{len(chain_nodes)} {RelationTypes.BELONGS_TO.value}")

            # 创建并关联投资方
            for institution_node in institution_nodes:
                await self.loader.create_institution(institution_node)
                await self.loader.relate_institution_to_project(
                    institution_node.name, project_node.name
                )
            if institution_nodes:
                result["nodes_created"].append(f"{len(institution_nodes)} Institutions")
                result["relationships_created"].append(f"{len(institution_nodes)} {RelationTypes.INVESTED.value}")

            # 创建并关联团队成员
            team_data = self.team_to_nodes(project)
            for person, relation_type in team_data:
                await self.loader.create_person(person)
                await self.loader.relate_person_to_project(
                    person.name, project_node.name, relation_type
                )
            if team_data:
                result["nodes_created"].append(f"{len(team_data)} Persons")
                result["relationships_created"].append(f"{len(team_data)} Team Relations")

            # 创建并关联融资轮次（含详细投资方和金额）
            funding_data = self.funding_to_relations(project)
            for inv_name, proj_name, round_type, amount in funding_data:
                await self.loader.create_institution(
                    InstitutionNode(name=inv_name)
                )
                await self.loader.relate_institution_to_project(
                    inv_name, proj_name, round_type, amount
                )
            if funding_data:
                result["nodes_created"].append(f"{len(funding_data)} Funding Investors")
                result["relationships_created"].append(f"{len(funding_data)} {RelationTypes.INVESTED.value} (detailed)")

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
