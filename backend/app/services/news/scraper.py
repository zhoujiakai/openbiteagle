"""Odaily news scraper.

Odaily 快讯页面是动态加载的，直接爬取 HTML 不可行。
这里提供一个模拟数据的爬虫用于测试，生产环境需要：
1. 使用 Playwright/Selenium 进行浏览器自动化
2. 或找到 Odaily 的 API 接口
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class NewsItem:
    """News item data structure."""

    title: str
    content: Optional[str] = None
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    published_at: Optional[datetime] = None


class OdailyScraper:
    """Odaily news scraper (mock implementation for testing).

    实际生产环境需要使用 Playwright 或 API 接口。
    """

    BASE_URL = "https://www.odaily.news"
    FLASH_URL = f"{BASE_URL}/flash"

    def __init__(self, timeout: int = 30, use_mock: bool = True):
        """Initialize scraper.

        Args:
            timeout: HTTP request timeout in seconds
            use_mock: Use mock data for testing (True by default)
        """
        self.timeout = timeout
        self.use_mock = use_mock

    async def __aenter__(self):
        """Enter context manager."""
        return self

    async def __aexit__(self, *args):
        """Exit context manager."""
        pass

    async def fetch_flash_news(self, limit: int = 50) -> list[NewsItem]:
        """Fetch flash news from Odaily.

        Args:
            limit: Maximum number of news items to fetch

        Returns:
            List of NewsItem
        """
        if self.use_mock:
            return self._get_mock_news(limit)

        # TODO: 实现 Playwright 爬虫或 API 调用
        return []

    def _get_mock_news(self, limit: int) -> list[NewsItem]:
        """Generate mock news for testing.

        Args:
            limit: Number of mock news items

        Returns:
            List of mock NewsItem
        """
        mock_titles = [
            "以太坊网络升级成功，Gas费用降低30%",
            "比特币ETF昨日净流入1.2亿美元",
            "Solana推出新开发者基金，规模达1000万美元",
            "币安获得新加坡支付服务许可证",
            "Cardano创始人发布新技术路线图",
            "Ripple与美国SEC达成和解协议",
            "PolygonLayer2网络交易量创历史新高",
            "Avalanche基金会宣布新的生态激励计划",
            "UniswapV4版本即将上线测试网",
            "Chainlink预言机服务集成至DeFi协议",
        ]

        mock_contents = [
            "本次升级主要优化了网络性能，降低了交易成本。",
            "机构投资者持续增持，显示市场信心增强。",
            "该基金旨在支持Solana生态内的创新项目发展。",
            "这意味着币安可以在新加坡提供合规的数字支付服务。",
            "新路线图聚焦于扩展性和去中心化治理。",
            "双方达成和解，结束了长达两年的法律纠纷。",
            "Layer2解决方案的采用率持续上升。",
            "激励计划涵盖DeFi、NFT和GameFi等多个领域。",
            "V4版本将引入更多自定义功能和流动性机制。",
            "集成后将提升DeFi协议的数据可靠性和安全性。",
        ]

        news_items = []
        now = datetime.now()

        for i in range(min(limit, len(mock_titles))):
            published_at = now - timedelta(minutes=i * 15)
            news_items.append(
                NewsItem(
                    title=mock_titles[i],
                    content=mock_contents[i],
                    source_url=f"{self.BASE_URL}/flash/post/{1000 + i}",
                    source_id=f"odaily-{1000 + i}",
                    published_at=published_at,
                )
            )

        return news_items

    async def fetch_news_by_id(self, news_id: str) -> Optional[NewsItem]:
        """Fetch a specific news article by ID.

        Args:
            news_id: Article ID

        Returns:
            NewsItem or None
        """
        if self.use_mock:
            # Return first mock news
            mock_news = self._get_mock_news(1)
            return mock_news[0] if mock_news else None
        return None


async def scrape_odaily_news(limit: int = 50) -> list[NewsItem]:
    """Convenience function to scrape Odaily news.

    Args:
        limit: Maximum number of news items to fetch

    Returns:
        List of NewsItem
    """
    async with OdailyScraper(use_mock=True) as scraper:
        return await scraper.fetch_flash_news(limit)
