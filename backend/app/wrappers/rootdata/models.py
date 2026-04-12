"""Data models for Rootdata scraper."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenInfo:
    """Token information from Rootdata."""

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
    """Whitepaper information."""

    title: str
    url: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class ProjectInfo:
    """Project information from Rootdata.

    This contains structured data about a Web3 project that can be
    imported into the knowledge base.
    """

    # Basic info
    rootdata_id: str
    name: str
    name_en: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None

    # Description
    description: Optional[str] = None
    description_en: Optional[str] = None
    introduction: Optional[str] = None  # Detailed introduction

    # Categories
    categories: list[str] = field(default_factory=list)
    chains: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # Token info
    token: Optional[TokenInfo] = None

    # Whitepaper
    whitepaper: Optional[Whitepaper] = None

    # Links
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    discord: Optional[str] = None
    github: Optional[str] = None
    docs_url: Optional[str] = None

    # Metadata
    funding_rounds: Optional[int] = None
    investors: list[str] = field(default_factory=list)

    # Source
    source_url: Optional[str] = None  # Rootdata project page URL

    def to_kb_document(self) -> dict:
        """Convert to knowledge base document format.

        Returns a dict suitable for insert_document().
        """
        # Build content from available fields
        content_parts = []

        # Description
        if self.introduction:
            content_parts.append(self.introduction)
        elif self.description:
            content_parts.append(self.description)
        elif self.description_en:
            content_parts.append(self.description_en)

        # Add token info
        if self.token:
            token_info = f"Token: {self.token.symbol} ({self.token.name})"
            if self.token.contract_address:
                token_info += f"\nContract: {self.token.contract_address}"
            content_parts.append(token_info)

        # Add whitepaper info
        if self.whitepaper and self.whitepaper.summary:
            content_parts.append(f"Whitepaper: {self.whitepaper.summary}")

        # Add categories and tags
        if self.categories:
            content_parts.append(f"Categories: {', '.join(self.categories)}")
        if self.tags:
            content_parts.append(f"Tags: {', '.join(self.tags)}")

        # Combine content
        content = "\n\n".join(content_parts) if content_parts else self.name

        # Extract tokens for metadata
        tokens = []
        if self.token:
            tokens.append(self.token.symbol)
        # Extract token symbols from tags
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
                "tokens": list(set(tokens)),  # Dedupe
                "investors": self.investors,
            },
        }

    @property
    def tokens_list(self) -> list[str]:
        """Get list of token symbols for this project."""
        tokens = []
        if self.token:
            tokens.append(self.token.symbol)
        # Extract from tags
        for tag in self.tags:
            if tag and len(tag) <= 10 and tag.isupper():
                tokens.append(tag)
        return list(set(tokens))
