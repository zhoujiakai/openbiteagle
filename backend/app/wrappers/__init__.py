"""Wrappers module.

Each data source has its own subdirectory with its own implementation.
"""

from app.wrappers.odaily import BaseNewsScraper, ContentResult, ImageInfo, NewsItem, OdailyScraper
from app.wrappers.oss import OSSClient
from app.wrappers.rootdata import ProjectInfo, RootdataClient, scrape_rootdata_projects

__all__ = [
    # Odaily
    "BaseNewsScraper",
    "ContentResult",
    "ImageInfo",
    "NewsItem",
    "OdailyScraper",
    # OSS
    "OSSClient",
    # Rootdata
    "ProjectInfo",
    "RootdataClient",
    "scrape_rootdata_projects",
]
