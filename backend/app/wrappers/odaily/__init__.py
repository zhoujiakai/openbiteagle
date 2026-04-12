"""Odaily news scraper wrapper."""

from app.wrappers.odaily.base import BaseNewsScraper, ContentResult, ImageInfo, NewsItem
from app.wrappers.odaily.odaily_scraper import OdailyScraper, OdailyDeepScraper

__all__ = [
    "BaseNewsScraper",
    "ContentResult",
    "ImageInfo",
    "NewsItem",
    "OdailyScraper",
    "OdailyDeepScraper",
]
