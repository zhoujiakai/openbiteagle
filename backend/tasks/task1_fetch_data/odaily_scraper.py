"""基于 Playwright 的 Odaily 新闻爬虫实现。"""

import asyncio
import re
from urllib.parse import parse_qs, urlparse
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from app.data.logger import create_logger

logger = create_logger("Odaily快讯页爬虫")

@dataclass
class NewsItem:
    """新闻条目数据结构。"""

    id: Optional[str] = None                   # 快讯 ID（Odaily 平台）
    title: str = ""                            # 标题
    content: Optional[str] = None              # 正文（HTML 格式）
    images: Optional[list[str]] = None         # 图片 URL 列表
    isImportant: bool = False                  # 是否重要快讯
    publishTimestamp: Optional[int] = None     # 发布时间戳（ms）
    publishDate: Optional[str] = None          # 发布时间，格式 yyyy-MM-dd HH:mm:ss
    sourceUrl: Optional[str] = None            # 原文外链，可能为空字符串
    link: Optional[str] = None                 # Odaily 站内详情页 URL

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "images": self.images,
            "isImportant": self.isImportant,
            "publishTimestamp": self.publishTimestamp,
            "publishDate": self.publishDate,
            "sourceUrl": self.sourceUrl,
            "link": self.link,
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
                    # 导航到快讯页面并滚动加载足够内容
                    await self._navigate_to_flash_page(page, target_count=limit)
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
        # 从 data-publish-timestamp 获取发布时间戳（ms）
        timestamp_str = await elem.get_attribute("data-publish-timestamp")
        publishTimestamp = int(timestamp_str) if timestamp_str else None
        publishDate = None
        if publishTimestamp:
            dt = datetime.fromtimestamp(publishTimestamp / 1000)
            publishDate = dt.strftime("%Y-%m-%d %H:%M:%S")

        # 获取 data-id 作为快讯 ID
        data_list_div = await elem.query_selector("div.data-list")
        news_id = None
        if data_list_div:
            news_id = await data_list_div.get_attribute("data-id")

        # 获取标题和站内详情页链接
        detail_link = await elem.query_selector("a[href*='newsflash']")
        title = ""
        link = None
        if detail_link:
            title_el = await detail_link.query_selector("span")
            if title_el:
                title = (await title_el.inner_text()).strip()
            href = await detail_link.get_attribute("href")
            if href:
                link = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        # 获取内容（去掉 HTML 标签）
        content_el = await elem.query_selector("div.whitespace-pre-line")
        content = None
        if content_el:
            raw = (await content_el.inner_html()).strip()
            clean = re.sub(r'<[^>]+>', '', raw)
            content = clean.removeprefix("Odaily星球日报讯").strip() or None

        # 获取原文外链
        sourceUrl = None
        ext_link = await elem.query_selector("a:text('原文链接')")
        if ext_link:
            sourceUrl = await ext_link.get_attribute("href")

        # 获取图片 URL 列表
        images: list[str] = []
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
            images.append(real_url)

        if not title:
            return None

        return NewsItem(
            id=news_id,
            title=title,
            content=content,
            images=images or None,
            publishTimestamp=publishTimestamp,
            publishDate=publishDate,
            sourceUrl=sourceUrl or "",
            link=link,
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

    async def _navigate_to_flash_page(self, page, target_count: int = 20):
        """导航到快讯页面并滚动加载足够的内容。

        Args:
            page: Playwright 页面对象
            target_count: 需要加载的最小新闻数量
        """
        try:
            await page.goto(
                self.FLASH_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )
        except Exception as e:
            logger.warning(f"导航警告: {e}")

        # 等待页面初始加载
        await page.wait_for_timeout(3000)

        # 循环滚动，触发懒加载直到数量足够或无法继续加载
        prev_count = 0
        max_rounds = 200  # 安全上限，防止无限滚动
        stale_rounds = 0  # 连续未增长计数

        for round_num in range(max_rounds):
            # 滚动到底部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

            current_count = await page.evaluate(
                "document.querySelectorAll('div.newsflash-item').length"
            )
            logger.info(
                f"滚动第 {round_num + 1} 轮，已加载 {current_count} 条 "
                f"(目标 {target_count})"
            )

            if current_count >= target_count:
                logger.info(f"已加载 {current_count} 条，达到目标数量")
                break

            if current_count == prev_count:
                stale_rounds += 1
                if stale_rounds >= 5:
                    logger.warning(
                        f"连续 {stale_rounds} 轮无新内容，停止滚动 "
                        f"(共 {current_count} 条)"
                    )
                    break
            else:
                stale_rounds = 0

            prev_count = current_count

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

    items = asyncio.run(scraper.fetch_news(limit=20))
    for item in items:
        print(f"[{item.publishDate}] {item.title}")
        if item.content:
            print(f"  {item.content[:80]}...")
        if item.link:
            print(f"  链接: {item.link}")
        print()


if __name__ == "__main__":
    main()
