"""基于 Playwright 的 Odaily 新闻爬虫实现。"""

import asyncio
from urllib.parse import parse_qs, urlparse
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.data.logger import create_logger

logger = create_logger("Odaily快讯页爬虫")

@dataclass
class ImageInfo:
    """从文章内容中提取的图片信息。"""

    url: str                    # 图片的 URL 地址
    alt: Optional[str] = None   # 图片的替代文本描述
    width: Optional[int] = None # 图片宽度
    height: Optional[int] = None # 图片高度

    def to_dict(self) -> dict:
        """转换为字典，用于数据库存储。"""
        return {
            "url": self.url,
            "alt": self.alt,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class NewsItem:
    """新闻条目数据结构。"""

    title: str                                  # 新闻标题
    content: Optional[str] = None               # 正文纯文本
    content_html: Optional[str] = None          # 正文 HTML
    page_url: Optional[str] = None              # 新闻源页面的链接（如 Odaily 快讯页）
    external_url: Optional[str] = None          # 原文外链（指向原始出处，可选）
    source_id: Optional[str] = None             # 新闻在来源平台的唯一 ID
    published_at: Optional[datetime] = None     # 发布时间
    images: Optional[list[ImageInfo]] = None    # 文章中的图片列表

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "title": self.title,
            "content": self.content,
            "content_html": self.content_html,
            "page_url": self.page_url,
            "external_url": self.external_url,
            "source_id": self.source_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "images": [img.to_dict() for img in self.images] if self.images else None,
        }


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

        # 获取图片
        images: list[ImageInfo] = []
        img_els = await elem.query_selector_all("button img[src]")
        for img_el in img_els:
            src = await img_el.get_attribute("src")
            if not src:
                continue
            # 从 /_next/image?url=xxx 中提取实际图片 URL
            if src.startswith("/_next/image?url="):
                parsed = urlparse(src)
                real_url = parse_qs(parsed.query).get("url", [src])[0]
            else:
                real_url = src
            alt = await img_el.get_attribute("alt")
            images.append(ImageInfo(url=real_url, alt=alt))

        if not title:
            return None

        return NewsItem(
            title=title,
            content=content,
            page_url=page_url,
            external_url=external_url,
            source_id=source_id,
            published_at=published_at,
            images=images or None,
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

    async def health_check(self) -> bool:
        """检查爬虫是否能连接到新闻源。

        Returns:
            连接成功返回 True，否则返回 False
        """
        try:
            items = await self.fetch_news(limit=1)
            return len(items) >= 0
        except Exception as e:
            return False



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
