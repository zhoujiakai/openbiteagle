"""RootData 数据模型定义。"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenInfo:
    """代币信息。"""

    symbol: str
    name: str
    price_usd: Optional[float] = None
    market_cap: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    contract_address: Optional[str] = None
    logo_url: Optional[str] = None


@dataclass
class Whitepaper:
    """白皮书信息。"""

    title: str
    url: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class ProjectInfo:
    """项目信息。

    包含 Web3 项目的结构化数据，可导入知识库。
    """

    # 基本信息
    rootdata_id: str
    name: str
    name_en: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None

    # 描述
    description: Optional[str] = None
    description_en: Optional[str] = None
    introduction: Optional[str] = None  # 详细介绍

    # 分类
    categories: list[str] = field(default_factory=list)
    chains: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # 代币信息
    token: Optional[TokenInfo] = None

    # 白皮书
    whitepaper: Optional[Whitepaper] = None

    # 社交链接
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    discord: Optional[str] = None
    github: Optional[str] = None
    docs_url: Optional[str] = None

    # 元数据
    funding_rounds: Optional[int] = None
    investors: list[str] = field(default_factory=list)

    # 来源
    source_url: Optional[str] = None  # RootData 项目页面 URL

    def to_kb_document(self) -> dict:
        """转换为知识库文档格式。

        Returns:
            适用于 insert_document() 的字典
        """
        # 从可用字段拼接内容
        content_parts = []

        # 描述
        if self.introduction:
            content_parts.append(self.introduction)
        elif self.description:
            content_parts.append(self.description)
        elif self.description_en:
            content_parts.append(self.description_en)

        # 代币信息
        if self.token:
            token_info = f"Token: {self.token.symbol} ({self.token.name})"
            if self.token.contract_address:
                token_info += f"\nContract: {self.token.contract_address}"
            content_parts.append(token_info)

        # 白皮书信息
        if self.whitepaper and self.whitepaper.summary:
            content_parts.append(f"Whitepaper: {self.whitepaper.summary}")

        # 分类和标签
        if self.categories:
            content_parts.append(f"Categories: {', '.join(self.categories)}")
        if self.tags:
            content_parts.append(f"Tags: {', '.join(self.tags)}")

        # 合并内容
        content = "\n\n".join(content_parts) if content_parts else self.name

        # 提取代币符号用于元数据
        tokens = []
        if self.token:
            tokens.append(self.token.symbol)
        # 从标签中提取代币符号
        for tag in self.tags:
            if tag and len(tag) <= 10 and tag.isupper():
                tokens.append(tag)

        return {
            "title": f"{self.name} - Project Overview",
            "content": content,
            "source_url": self.source_url or self.website_url,
            "source_type": "rootdata",
            "metadata": {
                "rootdata_id": self.rootdata_id,
                "name_en": self.name_en,
                "categories": self.categories,
                "chains": self.chains,
                "tokens": list(set(tokens)),  # 去重
                "investors": self.investors,
            },
        }

    @property
    def tokens_list(self) -> list[str]:
        """获取项目关联的代币符号列表。"""
        tokens = []
        if self.token:
            tokens.append(self.token.symbol)
        # 从标签中提取
        for tag in self.tags:
            if tag and len(tag) <= 10 and tag.isupper():
                tokens.append(tag)
        return list(set(tokens))
