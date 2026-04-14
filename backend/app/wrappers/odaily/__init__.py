"""Odaily 新闻爬虫封装。

实现来自 tasks.task1_fetch_data，本模块仅做重新导出。
"""

from tasks.task1_fetch_data.odaily_scraper import NewsItem, OdailyScraper
from tasks.task1_fetch_data.odaily_rest_scraper import OdailyRestScraper

__all__ = [
    "NewsItem",
    "OdailyScraper",
    "OdailyRestScraper",
]
