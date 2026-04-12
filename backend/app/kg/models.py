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

    ISSUED = "ISSUED"  # Token -[ISSUED]-> Project
    INVESTED = "INVESTED"  # Institution -[INVESTED]-> Project
    BELONGS_TO = "BELONGS_TO"  # Project -[BELONGS_TO]-> Chain
    COLLABORATES_WITH = "COLLABORATES_WITH"  # Project -[COLLABORATES_WITH]-> Project
    WORKS_AT = "WORKS_AT"  # Person -[WORKS_AT]-> Project
    ADVISES = "ADVISES"  # Person -[ADVISES]-> Project
    FOUNDED = "FOUNDED"  # Person -[FOUNDED]-> Project


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
    chain: Optional[str] = None  # e.g., "Ethereum", "Solana"
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
