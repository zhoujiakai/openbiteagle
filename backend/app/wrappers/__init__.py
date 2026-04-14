"""Wrappers module.

Each data source has its own subdirectory with its own implementation.
"""

from app.wrappers.odaily import NewsItem, OdailyScraper, OdailyRestScraper
from app.wrappers.oss import OSSClient
from app.wrappers.rootdata import ProjectInfo, RootdataClient, scrape_rootdata_projects

__all__ = [
    # Odaily 爬虫
    "NewsItem",
    "OdailyScraper",
    "OdailyRestScraper",
    # OSS 对象存储
    "OSSClient",
    # Rootdata 数据
    "ProjectInfo",
    "RootdataClient",
    "scrape_rootdata_projects",
]
