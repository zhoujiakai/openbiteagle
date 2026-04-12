"""基于 Playwright 的 Odaily 新闻爬虫实现。"""

import asyncio
from datetime import datetime
from typing import Optional

from base import NewsItem
from app.data.logger import create_logger

logger = create_logger("Odaily快讯页爬虫")

class OdailyScraper:
    """Odaily 新闻爬虫实现。

    使用 Playwright 处理动态页面加载。
    """

    BASE_URL = "https://www.odaily.news"
    FLASH_URL = f"{BASE_URL}/zh-CN/newsflash"

    def __init__(self, headless: bool = True):
        """初始化爬虫。

        Args:
            headless: 是否以无头模式运行浏览器
        """
        self.headless = headless

    @property
    def source_name(self) -> str:
        """返回新闻源名称。"""
        return "Odaily.Flash"

    async def fetch_news(self, limit: int) -> list[NewsItem]:
        """使用 Playwright 获取真实新闻。

        Args:
            limit: 最大获取数量

        Returns:
            NewsItem 对象列表
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser, page = await self._create_browser_page(p)
                if browser is None:
                    return []
                try:
                    # 导航到快讯页面
                    await self._navigate_to_flash_page(page)
                    # 从页面提取信息
                    items = await self._extract_news_items(page, limit)
                    logger.info(f"成功获取 {len(items)} 条新闻")
                    return items
                finally:
                    await browser.close()

        except ImportError:
            logger.error("Playwright 未安装")
            return []
        except Exception as e:
            logger.error(f"获取新闻时出错: {e}")
            return []

    async def _extract_news_items(self, page, limit: int) -> list[NewsItem]:
        """从页面中提取新闻条目。

        Args:
            page: Playwright 页面对象
            limit: 最大获取数量

        Returns:
            NewsItem 对象列表
        """
        news_items: list[NewsItem] = []

        elements = await page.query_selector_all("div.newsflash-item")
        logger.info(f"找到 {len(elements)} 个新闻元素")

        for elem in elements[:limit]:
            try:
                item = await self._parse_single_item(elem)
                if item:
                    news_items.append(item)
            except Exception as e:
                logger.warning(f"解析单条新闻失败: {e}")
                continue

        return news_items

    async def _parse_single_item(self, elem) -> Optional[NewsItem]:
        """解析单条新闻元素。

        Args:
            elem: Playwright ElementHandle

        Returns:
            NewsItem 或 None
        """
        # 从 data-publish-timestamp 获取发布时间
        timestamp_str = await elem.get_attribute("data-publish-timestamp")
        published_at = None
        if timestamp_str:
            published_at = datetime.fromtimestamp(int(timestamp_str) / 1000)

        # 获取 data-id 作为 source_id
        data_list_div = await elem.query_selector("div.data-list")
        source_id = None
        if data_list_div:
            source_id = await data_list_div.get_attribute("data-id")

        # 获取标题和快讯页链接
        detail_link = await elem.query_selector("a[href*='newsflash']")
        title = ""
        page_url = None
        if detail_link:
            title_el = await detail_link.query_selector("span")
            if title_el:
                title = (await title_el.inner_text()).strip()
            href = await detail_link.get_attribute("href")
            if href:
                page_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        # 获取内容
        content_el = await elem.query_selector("div.whitespace-pre-line")
        content = ""
        if content_el:
            content = (await content_el.inner_text()).strip().removeprefix("Odaily星球日报讯").strip()

        # 获取原文外链
        external_url = None
        ext_link = await elem.query_selector("a:text('原文链接')")
        if ext_link:
            external_url = await ext_link.get_attribute("href")

        if not title:
            return None

        return NewsItem(
            title=title,
            content=content,
            page_url=page_url,
            external_url=external_url,
            source_id=source_id,
            published_at=published_at,
        )

    async def _create_browser_page(self, playwright):
        """创建浏览器和页面实例。

        Returns:
            (browser, page) 元组，出错时返回 (None, None)
        """
        try:
            browser = await playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            return browser, page
        except Exception as e:
            logger.error(f"创建浏览器失败: {e}")
            return None, None

    async def _navigate_to_flash_page(self, page):
        """导航到快讯页面并等待内容加载。

        Args:
            page: Playwright 页面对象
        """
        try:
            await page.goto(
                self.FLASH_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )
        except Exception as e:
            logger.warning(f"导航警告: {e}")

        # 等待页面加载
        await page.wait_for_timeout(3000)

        # 滚动触发懒加载
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(2000)



def main():
    scraper = OdailyScraper(headless=True)
    items = asyncio.run(scraper.fetch_news(limit=10))
    for item in items:
        print(f"[{item.published_at}] {item.title}")
        if item.content:
            print(f"  {item.content[:80]}...")
        if item.page_url:
            print(f"  链接: {item.page_url}")
        print()


if __name__ == "__main__":
    main()
