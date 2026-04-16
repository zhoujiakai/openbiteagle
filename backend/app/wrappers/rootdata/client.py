"""RootData REST API 客户端，用于获取项目信息。

本模块使用 RootData REST API (https://api.rootdata.com/open)
替代 Playwright 网页爬虫，提供更稳定的数据访问。

使用的 API 端点：
- ser_inv: 按关键词搜索项目/机构/人物（免费，不限次数）
- get_item: 按 ID 获取项目详情（2 credits/次）
- quotacredits: 查询剩余 credits（免费）
"""

import asyncio
from typing import Optional

import httpx

from app.core.config import cfg
from app.data.logger import create_logger
from app.wrappers.rootdata.models import (
    FundingRound,
    InvestorBrief,
    ProjectInfo,
    TeamMember,
    TokenInfo,
)

logger = create_logger("RootData客户端")

# 用于发现 Web3 项目的热门搜索关键词
_DEFAULT_SEARCH_KEYWORDS = [
    "Bitcoin", "Ethereum", "DeFi", "NFT", "Layer2", "zk",
    "AI", "Gaming", "Social", "Infra", "Wallet", "Exchange",
    "Bridge", "Oracle", "Storage", "Privacy", "DAO",
]


class RootdataClient:
    """RootData REST API 客户端。"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 language: Optional[str] = None, timeout: Optional[float] = None):
        """初始化 API 客户端。

        Args:
            api_key: RootData API 密钥（默认从配置读取）
            base_url: API 基础 URL（默认从配置读取）
            language: 响应语言，'en' 英文或 'cn' 中文（默认从配置读取）
            timeout: 请求超时秒数（默认从配置读取）
        """
        self._api_key = api_key or cfg.rootdata.ROOTDATA_API_KEY
        self._base_url = (base_url or cfg.rootdata.ROOTDATA_BASE_URL).rstrip("/")
        self._language = language or cfg.rootdata.ROOTDATA_LANGUAGE
        self._timeout = timeout or cfg.rootdata.ROOTDATA_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> dict[str, str]:
        """构建通用请求头。"""
        return {
            "apikey": self._api_key,
            "language": self._language,
            "Content-Type": "application/json",
        }

    @property
    def client(self) -> httpx.AsyncClient:
        """延迟初始化 HTTP 客户端。"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口。"""
        await self.close()

    async def close(self):
        """关闭 HTTP 客户端。"""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── 底层 API 调用 ──────────────────────────────────

    async def _post(self, endpoint: str, payload: dict = None) -> dict:
        """向 RootData API 发送 POST 请求。

        Args:
            endpoint: API 端点路径（如 "ser_inv"）
            payload: JSON 请求体

        Returns:
            响应数据字典

        Raises:
            httpx.HTTPStatusError: 非 2xx 响应时抛出
            ValueError: API 层面错误（result != 200）时抛出
        """
        url = f"{self._base_url}/{endpoint}"
        resp = await self.client.post(url, json=payload or {}, headers=self._headers())
        resp.raise_for_status()
        body = resp.json()
        if body.get("result") != 200:
            raise ValueError(f"RootData API 错误: {body}")
        return body

    async def check_credits(self) -> dict:
        """查询剩余 API credits。

        Returns:
            包含 credits、total_credits、level 等字段的字典
        """
        body = await self._post("quotacredits")
        return body.get("data", {})

    async def search(self, query: str) -> list[dict]:
        """按关键词搜索项目/机构/人物。

        使用 ser_inv 端点，免费且不限次数。

        Args:
            query: 搜索关键词

        Returns:
            搜索结果列表，每项包含 id、type、name、logo 等字段
        """
        body = await self._post("ser_inv", {"query": query})
        return body.get("data", [])

    async def get_item(self, project_id: int, include_investors: bool = True,
                       include_team: bool = True) -> Optional[dict]:
        """按 ID 获取项目详细信息。

        使用 get_item 端点，消耗 2 credits/次。

        Args:
            project_id: RootData 项目 ID
            include_investors: 是否包含投资方信息
            include_team: 是否包含团队成员信息

        Returns:
            项目详情字典，失败返回 None
        """
        try:
            body = await self._post("get_item", {
                "project_id": project_id,
                "include_investors": include_investors,
                "include_team": include_team,
            })
            return body.get("data")
        except ValueError as e:
            logger.warning(f"get_item({project_id}) 失败: {e}")
            return None

    async def get_funding_rounds(self, project_id: int) -> list[FundingRound]:
        """获取指定项目的融资轮次信息。

        使用 get_fac 端点，消耗 2 credits/条。

        Args:
            project_id: RootData 项目 ID

        Returns:
            FundingRound 列表
        """
        try:
            body = await self._post("get_fac", {
                "project_id": project_id,
                "page_size": 50,
            })
            items = body.get("data", {}).get("items", [])
            rounds = []
            for item in items:
                # 解析金额
                amount = None
                raw_amount = item.get("amount") or item.get("funding_amount")
                if raw_amount is not None:
                    try:
                        amount = float(raw_amount)
                    except (ValueError, TypeError):
                        pass

                # 解析估值
                valuation = None
                raw_valuation = item.get("valuation")
                if raw_valuation is not None:
                    try:
                        valuation = float(raw_valuation)
                    except (ValueError, TypeError):
                        pass

                # 解析投资方列表
                round_investors = []
                for inv in item.get("investors", []):
                    inv_name = inv.get("name")
                    if inv_name:
                        round_investors.append(inv_name)

                rounds.append(FundingRound(
                    round_name=item.get("round_name") or item.get("round_type"),
                    amount=amount,
                    valuation=valuation,
                    date=item.get("date") or item.get("announced_time"),
                    investors=round_investors,
                ))
            return rounds
        except Exception as e:
            logger.warning(f"get_funding_rounds({project_id}) 失败: {e}")
            return []

    async def get_org(self, org_id: int) -> Optional[dict]:
        """获取机构详情。

        使用 get_org 端点，消耗 2 credits/次。

        Args:
            org_id: RootData 机构 ID

        Returns:
            机构详情字典，失败返回 None
        """
        try:
            body = await self._post("get_org", {"org_id": org_id})
            return body.get("data")
        except ValueError as e:
            logger.warning(f"get_org({org_id}) 失败: {e}")
            return None

    # ── 高层方法（保持原有接口不变）────────────────────

    async def get_project_list(self, limit: int = 50) -> list[dict]:
        """通过关键词搜索发现项目。

        Args:
            limit: 最多返回的项目数量

        Returns:
            包含 id、name、url、raw_data 键的字典列表
        """
        logger.info(f"正在发现项目（上限: {limit}）")

        seen_ids: set[int] = set()
        projects: list[dict] = []

        for keyword in _DEFAULT_SEARCH_KEYWORDS:
            if len(projects) >= limit:
                break

            try:
                results = await self.search(keyword)
            except Exception as e:
                logger.warning(f"搜索 '{keyword}' 失败: {e}")
                continue

            for item in results:
                # 仅保留 type 1（项目）
                if item.get("type") != 1:
                    continue
                pid = item.get("id")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                projects.append({
                    "id": str(pid),
                    "name": item.get("name", "Unknown"),
                    "url": item.get("rootdataurl", ""),
                    "raw_data": item,
                })
                if len(projects) >= limit:
                    break

            # 遵守速率限制（100 次/分钟）
            await asyncio.sleep(0.6)

        logger.info(f"共发现 {len(projects)} 个项目")
        return projects

    async def get_project_detail(self, project_id: str,
                                 raw_data: Optional[dict] = None) -> Optional[ProjectInfo]:
        """获取项目详细信息。

        Args:
            project_id: RootData 项目 ID（字符串）
            raw_data: 搜索结果的原始数据（备用，当详情获取失败时使用）

        Returns:
            ProjectInfo 对象，未找到则返回 None
        """
        pid = int(project_id)

        # 始终调用 get_item 获取完整详情
        # 搜索结果只包含基本字段，不足以填充 ProjectInfo
        detail = await self.get_item(pid)
        if detail is None:
            # 回退到解析搜索结果中的可用数据
            if raw_data:
                return self._parse_search_result(project_id, raw_data)
            return None

        return self._parse_project_data(project_id, detail)

    async def scrape_projects(self, limit: int = 20,
                              include_funding: bool = False) -> list[ProjectInfo]:
        """批量获取 RootData 项目。

        Args:
            limit: 最多获取的项目数量
            include_funding: 是否额外获取融资轮次详情（消耗更多 credits）

        Returns:
            ProjectInfo 对象列表
        """
        logger.info(f"开始从 RootData API 获取 {limit} 个项目")

        projects_list = await self.get_project_list(limit=limit)
        results = []

        for i, project in enumerate(projects_list):
            logger.info(f"正在获取项目 {i + 1}/{len(projects_list)}: {project['name']}")

            try:
                detail = await self.get_project_detail(
                    project["id"],
                    raw_data=project.get("raw_data"),
                )
                if detail:
                    # 可选补充融资轮次详情
                    if include_funding and detail.total_funding:
                        try:
                            funding_rounds = await self.get_funding_rounds(
                                int(project["id"])
                            )
                            detail.funding_details = funding_rounds
                        except Exception as e:
                            logger.warning(
                                f"获取项目 {detail.name} 融资轮次失败: {e}"
                            )
                        # 速率限制
                        await asyncio.sleep(0.6)
                    results.append(detail)
            except Exception as e:
                logger.error(f"获取项目 {project['name']} 时出错: {e}")

            # 速率限制：最多 100 次请求/分钟
            await asyncio.sleep(0.6)

        logger.info(f"成功获取 {len(results)} 个项目")
        return results

    # ── 解析辅助方法 ──────────────────────────────────

    def _parse_project_data(self, project_id: str, data: dict) -> Optional[ProjectInfo]:
        """解析 get_item API 返回的项目详情。

        Args:
            project_id: 项目 ID 字符串
            data: API 响应数据字典

        Returns:
            ProjectInfo 对象，解析失败返回 None
        """
        try:
            name = data.get("project_name", "Unknown")

            # 合并 one_liner 和 description 作为简介
            one_liner = data.get("one_liner", "")
            description = data.get("description", "")
            if one_liner and description:
                introduction = f"{one_liner}\n\n{description}"
            else:
                introduction = one_liner or description

            # 标签/分类
            tags = data.get("tags", [])
            categories = list(tags)

            # 链/生态
            chains = []
            for eco in data.get("ecosystem", []):
                if isinstance(eco, dict):
                    chain_name = eco.get("name") or eco.get("ecosystem_name", "")
                else:
                    chain_name = str(eco)
                if chain_name:
                    chains.append(chain_name)

            # 社交媒体
            social = data.get("social_media", {}) or {}
            website_url = social.get("website") or None
            twitter = social.get("twitter") or None
            discord = social.get("discord") or None
            telegram = social.get("telegram") or None
            github = social.get("github") or None

            # 代币信息
            token = None
            token_symbol = data.get("token_symbol")
            contracts = []
            if token_symbol:
                # 尝试从 contracts 中提取合约地址
                contract_address = None
                for contract in data.get("contracts", []):
                    addr = contract.get("contract_address")
                    if addr:
                        contracts.append(addr)
                        if contract_address is None:
                            contract_address = addr
                token = TokenInfo(
                    symbol=token_symbol,
                    name=token_symbol,
                    contract_address=contract_address,
                )

            # 投资方（名称列表 + 详情列表）
            investors = []
            investor_details = []
            for inv in data.get("investors", []):
                inv_name = inv.get("name")
                if inv_name:
                    investors.append(inv_name)
                    investor_details.append(InvestorBrief(
                        name=inv_name,
                        logo_url=inv.get("logo"),
                    ))

            # 团队成员
            team_members = []
            for member in data.get("team_members", []):
                member_name = member.get("name")
                if member_name:
                    team_members.append(TeamMember(
                        name=member_name,
                        position=member.get("position"),
                        twitter=member.get("twitter"),
                        linkedin=member.get("linkedin"),
                    ))

            # 融资总额和成立时间
            total_funding = data.get("total_funding")
            if total_funding is not None:
                try:
                    total_funding = float(total_funding)
                except (ValueError, TypeError):
                    total_funding = None

            establishment_date = data.get("establishment_date") or None

            # 来源 URL
            source_url = data.get("rootdataurl")

            return ProjectInfo(
                rootdata_id=str(project_id),
                name=name,
                name_en=name,
                description=description,
                introduction=introduction,
                categories=categories,
                chains=chains,
                tags=tags,
                token=token,
                logo_url=data.get("logo"),
                website_url=website_url,
                twitter=twitter,
                discord=discord,
                telegram=telegram,
                github=github,
                total_funding=total_funding,
                establishment_date=establishment_date,
                investors=investors,
                investor_details=investor_details,
                team_members=team_members,
                contracts=contracts,
                source_url=source_url,
            )
        except Exception as e:
            logger.error(f"解析项目数据时出错: {e}")
            return None

    def _parse_search_result(self, project_id: str, data: dict) -> Optional[ProjectInfo]:
        """从 ser_inv 搜索结果解析最基本的项目信息。

        Args:
            project_id: 项目 ID 字符串
            data: 搜索结果字典

        Returns:
            仅填充基本字段的 ProjectInfo 对象
        """
        try:
            name = data.get("name", "Unknown")
            return ProjectInfo(
                rootdata_id=str(project_id),
                name=name,
                name_en=name,
                description=data.get("introduce", ""),
                introduction=data.get("introduce", ""),
                logo_url=data.get("logo"),
                source_url=data.get("rootdataurl"),
            )
        except Exception as e:
            logger.error(f"解析搜索结果时出错: {e}")
            return None


# 便利函数 — 保持原有公开 API 不变
async def scrape_rootdata_projects(limit: int = 20) -> list[ProjectInfo]:
    """从 RootData API 获取项目列表。

    Args:
        limit: 最多获取的项目数量

    Returns:
        ProjectInfo 对象列表
    """
    async with RootdataClient() as client:
        return await client.scrape_projects(limit=limit)
