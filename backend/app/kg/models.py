"""Data models for Knowledge Graph nodes and relationships."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class NodeTypes(str, Enum):
    """Node type labels in Neo4j."""

    PROJECT = "Project"
    TOKEN = "Token"
    PERSON = "Person"
    INSTITUTION = "Institution"
    CHAIN = "Chain"


class RelationTypes(str, Enum):
    """Relationship types in Neo4j."""

    ISSUED = "ISSUED"  # 代币 -[发行]-> 项目
    INVESTED = "INVESTED"  # 机构 -[投资]-> 项目
    BELONGS_TO = "BELONGS_TO"  # 项目 -[属于]-> 公链
    COLLABORATES_WITH = "COLLABORATES_WITH"  # 项目 -[合作]-> 项目
    WORKS_AT = "WORKS_AT"  # 人物 -[任职于]-> 项目
    ADVISES = "ADVISES"  # 人物 -[顾问]-> 项目
    FOUNDED = "FOUNDED"  # 人物 -[创立]-> 项目


class PersonRole(str, Enum):
    """Person role types."""

    FOUNDER = "Founder"
    CEO = "CEO"
    CTO = "CTO"
    CO_FOUNDER = "Co-Founder"
    ADVISOR = "Advisor"
    TEAM_MEMBER = "Team Member"
    DEVELOPER = "Developer"


@dataclass
class ProjectNode:
    """Project node data."""

    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    discord: Optional[str] = None
    telegram: Optional[str] = None
    rootdata_id: Optional[str] = None
    logo_url: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Neo4j."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class TokenNode:
    """Token node data."""

    symbol: str
    name: str
    contract_address: Optional[str] = None
    chain: Optional[str] = None  # 例如 "Ethereum"、"Solana"
    coingecko_id: Optional[str] = None
    cmc_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Neo4j."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class PersonNode:
    """Person node data."""

    name: str
    role: Optional[PersonRole] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    rootdata_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Neo4j."""
        data = {k: v for k, v in self.__dict__.items() if v is not None}
        if isinstance(data.get("role"), PersonRole):
            data["role"] = data["role"].value
        return data


@dataclass
class InstitutionNode:
    """Institution node data."""

    name: str
    website: Optional[str] = None
    twitter: Optional[str] = None
    rootdata_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Neo4j."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class ChainNode:
    """Chain node data."""

    name: str
    description: Optional[str] = None
    website: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Neo4j."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Relationship:
    """Generic relationship data."""

    from_node_label: NodeTypes
    from_node_name: str
    relation_type: RelationTypes
    to_node_label: NodeTypes
    to_node_name: str
    properties: Optional[dict[str, Any]] = None
