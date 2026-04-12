"""Wrappers for news scraping.

This module provides a decoupled interface for news scraping,
allowing different news sources to be added without changing
the business logic layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ImageInfo:
    """Image information extracted from article content."""

    url: str
    alt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "url": self.url,
            "alt": self.alt,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class NewsItem:
    """News item data structure."""

    title: str
    content: Optional[str] = None
    content_html: Optional[str] = None
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    published_at: Optional[datetime] = None
    images: Optional[list[ImageInfo]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "content": self.content,
            "content_html": self.content_html,
            "source_url": self.source_url,
            "source_id": self.source_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "images": [img.to_dict() for img in self.images] if self.images else None,
        }


@dataclass
class ContentResult:
    """Content extraction result from detail pages."""

    text: Optional[str] = None
    html: Optional[str] = None
    images: list[ImageInfo] = field(default_factory=list)

    @property
    def has_content(self) -> bool:
        """Check if content was successfully extracted."""
        return bool(self.text)


class BaseNewsScraper(ABC):
    """Abstract base class for news scrapers.

    All news source scrapers should inherit from this class
    and implement the required methods.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the news source."""

    @abstractmethod
    async def fetch_news(self, limit: int = 50) -> list[NewsItem]:
        """Fetch a list of news items.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List of NewsItem objects
        """

    @abstractmethod
    async def fetch_news_detail(self, news_id: str) -> Optional[NewsItem]:
        """Fetch a single news item by its ID.

        Args:
            news_id: Unique identifier for the news item

        Returns:
            NewsItem object or None if not found
        """

    async def health_check(self) -> bool:
        """Check if the scraper can connect to the news source.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            items = await self.fetch_news(limit=1)
            return len(items) >= 0
        except Exception:
            return False
