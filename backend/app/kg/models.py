"""知识图谱节点和关系的数据模型。"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class NodeTypes(str, Enum):
    """Neo4j 中的节点类型标签。"""

    PROJECT = "Project"
    TOKEN = "Token"
    PERSON = "Person"
    INSTITUTION = "Institution"
    CHAIN = "Chain"


class RelationTypes(str, Enum):
    """Neo4j 中的关系类型。"""

    ISSUED = "ISSUED"  # 代币 -[发行]-> 项目
    INVESTED = "INVESTED"  # 机构 -[投资]-> 项目
    BELONGS_TO = "BELONGS_TO"  # 项目 -[属于]-> 公链
    COLLABORATES_WITH = "COLLABORATES_WITH"  # 项目 -[合作]-> 项目
    WORKS_AT = "WORKS_AT"  # 人物 -[任职于]-> 项目
    ADVISES = "ADVISES"  # 人物 -[顾问]-> 项目
    FOUNDED = "FOUNDED"  # 人物 -[创立]-> 项目


class PersonRole(str, Enum):
    """人物角色类型。"""

    FOUNDER = "Founder"
    CEO = "CEO"
    CTO = "CTO"
    CO_FOUNDER = "Co-Founder"
    ADVISOR = "Advisor"
    TEAM_MEMBER = "Team Member"
    DEVELOPER = "Developer"


@dataclass
class ProjectNode:
    """项目节点数据。"""

    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    discord: Optional[str] = None
    telegram: Optional[str] = None
    rootdata_id: Optional[str] = None
    logo_url: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为 Neo4j 使用的字典。"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class TokenNode:
    """代币节点数据。"""

    symbol: str
    name: str
    contract_address: Optional[str] = None
    chain: Optional[str] = None  # 例如 "Ethereum"、"Solana"
    coingecko_id: Optional[str] = None
    cmc_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为 Neo4j 使用的字典。"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class PersonNode:
    """人物节点数据。"""

    name: str
    role: Optional[PersonRole] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    rootdata_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为 Neo4j 使用的字典。"""
        data = {k: v for k, v in self.__dict__.items() if v is not None}
        if isinstance(data.get("role"), PersonRole):
            data["role"] = data["role"].value
        return data


@dataclass
class InstitutionNode:
    """机构节点数据。"""

    name: str
    website: Optional[str] = None
    twitter: Optional[str] = None
    rootdata_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为 Neo4j 使用的字典。"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class ChainNode:
    """公链节点数据。"""

    name: str
    description: Optional[str] = None
    website: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为 Neo4j 使用的字典。"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Relationship:
    """通用关系数据。"""

    from_node_label: NodeTypes
    from_node_name: str
    relation_type: RelationTypes
    to_node_label: NodeTypes
    to_node_name: str
    properties: Optional[dict[str, Any]] = None
