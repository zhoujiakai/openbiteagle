"""封装器模块。

每个数据源都有自己的子目录和实现。
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
