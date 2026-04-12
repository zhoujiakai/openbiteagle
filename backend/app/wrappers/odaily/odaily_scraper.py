"""Odaily news scraper implementation using Playwright."""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional

from app.wrappers.odaily.base import BaseNewsScraper, ContentResult, ImageInfo, NewsItem


class OdailyScraper(BaseNewsScraper):
    """Odaily news scraper implementation.

    Uses Playwright to handle dynamic page loading.
    """

    BASE_URL = "https://www.odaily.news"
    FLASH_URL = f"{BASE_URL}/flash"
    DETAIL_PATH = "/post/"

    def __init__(self, use_mock: bool = True, headless: bool = True):
        """Initialize the scraper.

        Args:
            use_mock: Use mock data for testing (True by default)
            headless: Run browser in headless mode
        """
        self.use_mock = use_mock
        self.headless = headless

    @property
    def source_name(self) -> str:
        """Return the name of the news source."""
        return "odaily"

    async def fetch_news(self, limit: int = 50) -> list[NewsItem]:
        """Fetch news from Odaily.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List of NewsItem objects
        """
        if self.use_mock:
            return await self._fetch_mock_news(limit)

        return await self._fetch_real_news(limit)

    async def fetch_news_detail(self, news_id: str) -> Optional[NewsItem]:
        """Fetch a single news item by ID.

        Args:
            news_id: Unique identifier (e.g., "odaily-5209519")

        Returns:
            NewsItem object or None
        """
        if self.use_mock:
            mock_news = await self._fetch_mock_news(1)
            return mock_news[0] if mock_news else None

        # Extract numeric ID from "odaily-xxxxx"
        numeric_id = news_id.split("-")[-1] if "-" in news_id else news_id
        detail_url = f"{self.BASE_URL}/post/{numeric_id}"

        return await self._fetch_single_detail(detail_url, numeric_id)

    async def _fetch_real_news(self, limit: int) -> list[NewsItem]:
        """Fetch real news using Playwright.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List of NewsItem objects
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser, page = await self._create_browser_page(p)
                if browser is None:
                    return await self._fetch_mock_news(limit)

                try:
                    # Navigate to flash page
                    await self._navigate_to_flash_page(page)

                    # Get news links from the list page
                    news_links = await self._get_news_links(page, limit)
                    if not news_links:
                        print("No news links found, falling back to mock data")
                        return await self._fetch_mock_news(limit)

                    print(f"Found {len(news_links)} news links")

                    # Fetch content for each news detail page
                    items = await self._fetch_news_details(browser, news_links, limit)

                    return items[:limit]

                finally:
                    await browser.close()

        except ImportError:
            print("Playwright not installed, using mock data")
            return await self._fetch_mock_news(limit)
        except Exception as e:
            print(f"Error fetching real news: {e}")
            return await self._fetch_mock_news(limit)

    async def _create_browser_page(self, playwright):
        """Create browser and page instances.

        Returns:
            Tuple of (browser, page) or (None, None) on error
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
            print(f"Failed to create browser: {e}")
            return None, None

    async def _navigate_to_flash_page(self, page):
        """Navigate to flash page and wait for content to load.

        Args:
            page: Playwright page object
        """
        try:
            await page.goto(
                self.FLASH_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )
        except Exception as e:
            print(f"Navigation warning: {e}")

        # Wait for page to load
        await page.wait_for_timeout(3000)

        # Scroll to trigger lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(2000)

    async def _get_news_links(self, page, limit: int) -> list[dict]:
        """Extract news links from the flash page.

        Args:
            page: Playwright page object
            limit: Maximum number of links to extract

        Returns:
            List of dict with 'href' and 'title' keys
        """
        links = []

        # Primary selector for Odaily news links
        selectors = [
            "a[href*='/post/']",
            "a[href*='/flash/']",
        ]

        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 3:
                    print(f"Found {len(elements)} potential links with selector: {selector}")

                    seen_hrefs = set()

                    for element in elements[:limit * 2]:  # Get more than needed for filtering
                        try:
                            href = await element.get_attribute("href")
                            title = await element.inner_text()

                            if not href or not title:
                                continue

                            # Clean up
                            title = title.strip()
                            if len(title) < 5:
                                continue

                            # Skip error messages
                            if "错误" in title or "error" in title.lower():
                                continue

                            # Deduplicate by href
                            if href in seen_hrefs:
                                continue
                            seen_hrefs.add(href)

                            # Build full URL if needed
                            if href.startswith("/"):
                                full_url = f"{self.BASE_URL}{href}"
                            else:
                                full_url = href

                            # Extract numeric ID from URL
                            id_match = re.search(r'/(\d+)/?$', href)
                            numeric_id = id_match.group(1) if id_match else None

                            links.append({
                                "href": href,
                                "url": full_url,
                                "title": title,
                                "numeric_id": numeric_id,
                            })

                            if len(links) >= limit:
                                break

                        except Exception:
                            continue

                    if links:
                        break

            except Exception as e:
                print(f"Error with selector {selector}: {e}")
                continue

        return links

    async def _fetch_news_details(
        self,
        browser,
        news_links: list[dict],
        limit: int,
        max_concurrent: int = 1,
    ) -> list[NewsItem]:
        """Fetch full content for each news item by visiting detail pages.

        Args:
            browser: Playwright browser instance
            news_links: List of link dicts with href, url, title, numeric_id
            limit: Maximum number of items to process
            max_concurrent: Maximum concurrent page requests (default: 1 for stability)

        Returns:
            List of NewsItem objects with content
        """
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)
        seen_ids = set()

        async def fetch_one(link_data: dict) -> Optional[NewsItem]:
            """Fetch a single news item detail."""
            async with semaphore:
                source_id = (
                    f"odaily-{link_data['numeric_id']}"
                    if link_data.get('numeric_id')
                    else None
                )

                # Skip duplicates
                if source_id and source_id in seen_ids:
                    return None
                seen_ids.add(source_id)

                page = None
                try:
                    page = await browser.new_page()
                    content_result = await self._fetch_detail_content(
                        page, link_data['url']
                    )

                    return NewsItem(
                        title=link_data['title'],
                        content=content_result.text,
                        content_html=content_result.html,
                        source_url=link_data['url'],
                        source_id=source_id,
                        published_at=datetime.now(),  # TODO: extract from page
                        images=content_result.images,
                    )

                except Exception as e:
                    print(f"Error fetching detail for {link_data.get('url')}: {e}")
                    return None
                finally:
                    if page:
                        await page.close()

        # Create tasks for all links
        tasks = [fetch_one(link_data) for link_data in news_links[:limit]]

        # Execute concurrently and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None and exceptions
        items = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Task exception: {result}")
                continue
            if result is not None:
                items.append(result)

        return items

    async def _fetch_detail_content(
        self, page, detail_url: str
    ) -> ContentResult:
        """Fetch content (text and HTML) and images from a news detail page.

        Args:
            page: Playwright page object
            detail_url: Full URL of the detail page

        Returns:
            ContentResult with text, html, and images
        """
        try:
            await page.goto(detail_url, timeout=30000)
            await page.wait_for_timeout(2000)

            # Try multiple selectors for content (Odaily-specific first)
            content_selectors = [
                ".DetailContent_detail__pRaS_",  # Odaily article body
                "article",
                "[class*='article']",
                "[class*='content']",
                ".article-content",
            ]

            for selector in content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 20:
                            # Clean up text: remove extra whitespace
                            text = ' '.join(text.split())

                            # Get HTML with image tags preserved
                            html = await element.inner_html()

                            # Extract images from the same element
                            images = await self._extract_images(element)

                            return ContentResult(text=text, html=html, images=images)
                except Exception:
                    continue

        except Exception as e:
            print(f"Error fetching detail page {detail_url}: {e}")

        return ContentResult()

    async def _extract_images(self, element) -> list[ImageInfo]:
        """Extract image information from a content element.

        Args:
            element: Playwright element handle

        Returns:
            List of unique ImageInfo objects
        """
        images = []
        try:
            img_elements = await element.query_selector_all("img")
            for img in img_elements:
                src = await img.get_attribute("src")
                if not src or not src.startswith("http"):
                    continue

                # Extract alt text
                alt = await img.get_attribute("alt")

                # Extract natural dimensions
                width = await img.evaluate("el => el.naturalWidth")
                height = await img.evaluate("el => el.naturalHeight")

                # Filter out invalid dimensions (0 means not loaded)
                if width == 0:
                    width = None
                if height == 0:
                    height = None

                images.append(ImageInfo(url=src, alt=alt, width=width, height=height))
        except Exception:
            pass

        # Deduplicate by URL while preserving order
        seen = set()
        unique_images = []
        for img in images:
            if img.url not in seen:
                seen.add(img.url)
                unique_images.append(img)

        return unique_images

    async def _fetch_single_detail(self, detail_url: str, numeric_id: str) -> Optional[NewsItem]:
        """Fetch a single news item by detail page URL.

        Args:
            detail_url: Full URL of the detail page
            numeric_id: Numeric ID for the news

        Returns:
            NewsItem object or None
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                try:
                    await page.goto(detail_url, timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Extract title
                    title_elem = await page.query_selector("h1, h2, [class*='title']")
                    title = await title_elem.inner_text() if title_elem else "Unknown"

                    # Extract content
                    content_result = await self._fetch_detail_content(page, detail_url)

                    return NewsItem(
                        title=title.strip(),
                        content=content_result.text,
                        content_html=content_result.html,
                        source_url=detail_url,
                        source_id=f"odaily-{numeric_id}",
                        images=content_result.images,
                    )

                finally:
                    await browser.close()

        except Exception:
            return None

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """Parse time string to datetime.

        Args:
            time_str: Time string from the page

        Returns:
            datetime or None
        """
        time_str = time_str.strip()

        # Handle relative time like "5分钟前"
        if "分钟前" in time_str:
            minutes = int(time_str.replace("分钟前", "").strip())
            return datetime.now() - timedelta(minutes=minutes)
        elif "小时前" in time_str:
            hours = int(time_str.replace("小时前", "").strip())
            return datetime.now() - timedelta(hours=hours)
        elif "天前" in time_str:
            days = int(time_str.replace("天前", "").strip())
            return datetime.now() - timedelta(days=days)
        elif "刚刚" in time_str:
            return datetime.now()

        # Try common date formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m-%d %H:%M",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue

        return None

    async def _fetch_mock_news(self, limit: int) -> list[NewsItem]:
        """Generate mock news for testing.

        Args:
            limit: Number of mock items to generate

        Returns:
            List of mock NewsItem objects
        """
        mock_data = [
            {
                "title": "以太坊网络升级成功，Gas费用降低30%",
                "content": "本次升级主要优化了网络性能，降低了交易成本。",
                "source_url": f"{self.BASE_URL}/flash/post/1000",
                "source_id": "odaily-1000",
            },
            {
                "title": "比特币ETF昨日净流入1.2亿美元",
                "content": "机构投资者持续增持，显示市场信心增强。",
                "source_url": f"{self.BASE_URL}/flash/post/1001",
                "source_id": "odaily-1001",
            },
            {
                "title": "Solana推出新开发者基金，规模达1000万美元",
                "content": "该基金旨在支持Solana生态内的创新项目发展。",
                "source_url": f"{self.BASE_URL}/flash/post/1002",
                "source_id": "odaily-1002",
            },
            {
                "title": "币安获得新加坡支付服务许可证",
                "content": "这意味着币安可以在新加坡提供合规的数字支付服务。",
                "source_url": f"{self.BASE_URL}/flash/post/1003",
                "source_id": "odaily-1003",
            },
            {
                "title": "Cardano创始人发布新技术路线图",
                "content": "新路线图聚焦于扩展性和去中心化治理。",
                "source_url": f"{self.BASE_URL}/flash/post/1004",
                "source_id": "odaily-1004",
            },
            {
                "title": "Ripple与美国SEC达成和解协议",
                "content": "双方达成和解，结束了长达两年的法律纠纷。",
                "source_url": f"{self.BASE_URL}/flash/post/1005",
                "source_id": "odaily-1005",
            },
            {
                "title": "Polygon Layer2网络交易量创历史新高",
                "content": "Layer2解决方案的采用率持续上升。",
                "source_url": f"{self.BASE_URL}/flash/post/1006",
                "source_id": "odaily-1006",
            },
            {
                "title": "Avalanche基金会宣布新的生态激励计划",
                "content": "激励计划涵盖DeFi、NFT和GameFi等多个领域。",
                "source_url": f"{self.BASE_URL}/flash/post/1007",
                "source_id": "odaily-1007",
            },
            {
                "title": "Uniswap V4版本即将上线测试网",
                "content": "V4版本将引入更多自定义功能和流动性机制。",
                "source_url": f"{self.BASE_URL}/flash/post/1008",
                "source_id": "odaily-1008",
            },
            {
                "title": "Chainlink预言机服务集成至DeFi协议",
                "content": "集成后将提升DeFi协议的数据可靠性和安全性。",
                "source_url": f"{self.BASE_URL}/flash/post/1009",
                "source_id": "odaily-1009",
            },
        ]

        items = []
        now = datetime.now()

        for i, data in enumerate(mock_data[:limit]):
            # Simulate decreasing publish time
            published_at = datetime.fromtimestamp(now.timestamp() - i * 900)

            items.append(
                NewsItem(
                    title=data["title"],
                    content=data["content"],
                    source_url=data["source_url"],
                    source_id=data["source_id"],
                    published_at=published_at,
                )
            )

        return items


class OdailyDeepScraper(BaseNewsScraper):
    """Odaily deep article scraper implementation.

    Scrapes in-depth articles from https://www.odaily.news/zh-CN/deep
    Uses Playwright to handle dynamic page loading.
    """

    BASE_URL = "https://www.odaily.news"
    DEEP_URL = f"{BASE_URL}/zh-CN/deep"

    def __init__(self, use_mock: bool = True, headless: bool = True):
        """Initialize the scraper.

        Args:
            use_mock: Use mock data for testing (True by default)
            headless: Run browser in headless mode
        """
        self.use_mock = use_mock
        self.headless = headless

    @property
    def source_name(self) -> str:
        """Return the name of the news source."""
        return "odaily-deep"

    async def fetch_news(self, limit: int = 50) -> list[NewsItem]:
        """Fetch deep articles from Odaily.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List of NewsItem objects
        """
        if self.use_mock:
            return await self._fetch_mock_deep_articles(limit)

        return await self._fetch_real_deep_articles(limit)

    async def fetch_news_detail(self, news_id: str) -> Optional[NewsItem]:
        """Fetch a single deep article by ID.

        Args:
            news_id: Unique identifier (e.g., "odaily-deep-5209519")

        Returns:
            NewsItem object or None
        """
        if self.use_mock:
            mock_articles = await self._fetch_mock_deep_articles(1)
            return mock_articles[0] if mock_articles else None

        # Extract numeric ID from "odaily-deep-xxxxx"
        numeric_id = news_id.split("-")[-1] if "-" in news_id else news_id
        detail_url = f"{self.BASE_URL}/post/{numeric_id}"

        return await self._fetch_single_deep_detail(detail_url, numeric_id)

    async def _fetch_real_deep_articles(self, limit: int) -> list[NewsItem]:
        """Fetch real deep articles using Playwright.

        Args:
            limit: Maximum number of items to fetch

        Returns:
            List of NewsItem objects
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser, page = await self._create_browser_page(p)
                if browser is None:
                    return await self._fetch_mock_deep_articles(limit)

                try:
                    # Navigate to deep articles page
                    await self._navigate_to_deep_page(page)

                    # Get article links from the deep page
                    article_links = await self._get_deep_article_links(page, limit)
                    if not article_links:
                        print("No deep article links found, falling back to mock data")
                        return await self._fetch_mock_deep_articles(limit)

                    print(f"Found {len(article_links)} deep article links")

                    # Fetch content for each article detail page
                    items = await self._fetch_deep_article_details(browser, article_links, limit)

                    return items[:limit]

                finally:
                    await browser.close()

        except ImportError:
            print("Playwright not installed, using mock data")
            return await self._fetch_mock_deep_articles(limit)
        except Exception as e:
            print(f"Error fetching real deep articles: {e}")
            return await self._fetch_mock_deep_articles(limit)

    async def _create_browser_page(self, playwright):
        """Create browser and page instances.

        Returns:
            Tuple of (browser, page) or (None, None) on error
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
            print(f"Failed to create browser: {e}")
            return None, None

    async def _navigate_to_deep_page(self, page):
        """Navigate to deep articles page and wait for content to load.

        Args:
            page: Playwright page object
        """
        try:
            await page.goto(
                self.DEEP_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )
        except Exception as e:
            print(f"Navigation warning: {e}")

        # Wait for page to load
        await page.wait_for_timeout(3000)

        # Scroll to trigger lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(2000)

    async def _get_deep_article_links(self, page, limit: int) -> list[dict]:
        """Extract deep article links from the deep articles page.

        Args:
            page: Playwright page object
            limit: Maximum number of links to extract

        Returns:
            List of dict with 'href', 'url', 'title', 'numeric_id' keys
        """
        links = []

        # Selectors for deep article cards on Odaily
        selectors = [
            "a[href*='/post/']",
            ".deep-article-item a",
            "[class*='DeepArticle'] a",
            "[class*='article-card'] a",
        ]

        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 3:
                    print(f"Found {len(elements)} potential links with selector: {selector}")

                    seen_hrefs = set()

                    for element in elements[:limit * 2]:
                        try:
                            href = await element.get_attribute("href")
                            title = await element.inner_text()

                            if not href or not title:
                                continue

                            # Clean up
                            title = title.strip()
                            if len(title) < 5:
                                continue

                            # Skip error messages
                            if "错误" in title or "error" in title.lower():
                                continue

                            # Deduplicate by href
                            if href in seen_hrefs:
                                continue
                            seen_hrefs.add(href)

                            # Build full URL if needed
                            if href.startswith("/"):
                                full_url = f"{self.BASE_URL}{href}"
                            else:
                                full_url = href

                            # Extract numeric ID from URL
                            id_match = re.search(r'/post/(\d+)/?', href)
                            numeric_id = id_match.group(1) if id_match else None

                            links.append({
                                "href": href,
                                "url": full_url,
                                "title": title,
                                "numeric_id": numeric_id,
                            })

                            if len(links) >= limit:
                                break

                        except Exception:
                            continue

                    if links:
                        break

            except Exception as e:
                print(f"Error with selector {selector}: {e}")
                continue

        return links

    async def _fetch_deep_article_details(
        self,
        browser,
        article_links: list[dict],
        limit: int,
        max_concurrent: int = 1,
    ) -> list[NewsItem]:
        """Fetch full content for each deep article by visiting detail pages.

        Args:
            browser: Playwright browser instance
            article_links: List of link dicts with href, url, title, numeric_id
            limit: Maximum number of items to process
            max_concurrent: Maximum concurrent page requests

        Returns:
            List of NewsItem objects with content
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        seen_ids = set()

        async def fetch_one(link_data: dict) -> Optional[NewsItem]:
            """Fetch a single deep article detail."""
            async with semaphore:
                source_id = (
                    f"odaily-deep-{link_data['numeric_id']}"
                    if link_data.get('numeric_id')
                    else None
                )

                # Skip duplicates
                if source_id and source_id in seen_ids:
                    return None
                seen_ids.add(source_id)

                page = None
                try:
                    page = await browser.new_page()
                    content_result = await self._fetch_deep_detail_content(
                        page, link_data['url']
                    )

                    # Try to extract publish time from page
                    published_at = await self._extract_publish_time(page)

                    return NewsItem(
                        title=link_data['title'],
                        content=content_result.text,
                        content_html=content_result.html,
                        source_url=link_data['url'],
                        source_id=source_id,
                        published_at=published_at,
                        images=content_result.images,
                    )

                except Exception as e:
                    print(f"Error fetching detail for {link_data.get('url')}: {e}")
                    return None
                finally:
                    if page:
                        await page.close()

        # Create tasks for all links
        tasks = [fetch_one(link_data) for link_data in article_links[:limit]]

        # Execute concurrently and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None and exceptions
        items = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Task exception: {result}")
                continue
            if result is not None:
                items.append(result)

        return items

    async def _fetch_deep_detail_content(
        self, page, detail_url: str
    ) -> ContentResult:
        """Fetch content (text and HTML) and images from a deep article detail page.

        Args:
            page: Playwright page object
            detail_url: Full URL of the detail page

        Returns:
            ContentResult with text, html, and images
        """
        try:
            await page.goto(detail_url, timeout=30000)
            await page.wait_for_timeout(2000)

            # Try multiple selectors for content (Odaily deep article first)
            content_selectors = [
                ".DetailContent_detail__pRaS_",  # Odaily article body
                ".article-content",
                "[class*='articleBody']",
                "[class*='content-body']",
                "article",
                "[class*='detail-content']",
            ]

            for selector in content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 20:
                            # Clean up text: remove extra whitespace
                            text = ' '.join(text.split())

                            # Get HTML with image tags preserved
                            html = await element.inner_html()

                            # Extract images from the same element
                            images = await self._extract_images(element)

                            return ContentResult(text=text, html=html, images=images)
                except Exception:
                    continue

        except Exception as e:
            print(f"Error fetching detail page {detail_url}: {e}")

        return ContentResult()

    async def _extract_publish_time(self, page) -> Optional[datetime]:
        """Extract publish time from the detail page.

        Args:
            page: Playwright page object

        Returns:
            datetime or None
        """
        try:
            # Try various time selectors
            time_selectors = [
                "[class*='time']",
                "[class*='date']",
                "[class*='publish']",
                "time",
            ]

            for selector in time_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        time_text = await element.inner_text()
                        if time_text:
                            parsed_time = self._parse_time(time_text)
                            if parsed_time:
                                return parsed_time
                except Exception:
                    continue
        except Exception:
            pass

        return None

    async def _extract_images(self, element) -> list[ImageInfo]:
        """Extract image information from a content element.

        Args:
            element: Playwright element handle

        Returns:
            List of unique ImageInfo objects
        """
        images = []
        try:
            img_elements = await element.query_selector_all("img")
            for img in img_elements:
                src = await img.get_attribute("src")
                if not src or not src.startswith("http"):
                    continue

                # Extract alt text
                alt = await img.get_attribute("alt")

                # Extract natural dimensions
                width = await img.evaluate("el => el.naturalWidth")
                height = await img.evaluate("el => el.naturalHeight")

                # Filter out invalid dimensions (0 means not loaded)
                if width == 0:
                    width = None
                if height == 0:
                    height = None

                images.append(ImageInfo(url=src, alt=alt, width=width, height=height))
        except Exception:
            pass

        # Deduplicate by URL while preserving order
        seen = set()
        unique_images = []
        for img in images:
            if img.url not in seen:
                seen.add(img.url)
                unique_images.append(img)

        return unique_images

    async def _fetch_single_deep_detail(self, detail_url: str, numeric_id: str) -> Optional[NewsItem]:
        """Fetch a single deep article by detail page URL.

        Args:
            detail_url: Full URL of the detail page
            numeric_id: Numeric ID for the article

        Returns:
            NewsItem object or None
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                try:
                    await page.goto(detail_url, timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Extract title
                    title_elem = await page.query_selector("h1, [class*='title']")
                    title = await title_elem.inner_text() if title_elem else "Unknown"

                    # Extract content
                    content_result = await self._fetch_deep_detail_content(page, detail_url)

                    # Extract publish time
                    published_at = await self._extract_publish_time(page)

                    return NewsItem(
                        title=title.strip(),
                        content=content_result.text,
                        content_html=content_result.html,
                        source_url=detail_url,
                        source_id=f"odaily-deep-{numeric_id}",
                        published_at=published_at,
                        images=content_result.images,
                    )

                finally:
                    await browser.close()

        except Exception:
            return None

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """Parse time string to datetime.

        Args:
            time_str: Time string from the page

        Returns:
            datetime or None
        """
        time_str = time_str.strip()

        # Handle relative time like "5分钟前"
        if "分钟前" in time_str:
            minutes = int(time_str.replace("分钟前", "").strip())
            return datetime.now() - timedelta(minutes=minutes)
        elif "小时前" in time_str:
            hours = int(time_str.replace("小时前", "").strip())
            return datetime.now() - timedelta(hours=hours)
        elif "天前" in time_str:
            days = int(time_str.replace("天前", "").strip())
            return datetime.now() - timedelta(days=days)
        elif "刚刚" in time_str:
            return datetime.now()

        # Try common date formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m-%d %H:%M",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue

        return None

    async def _fetch_mock_deep_articles(self, limit: int) -> list[NewsItem]:
        """Generate mock deep articles for testing.

        Args:
            limit: Number of mock items to generate

        Returns:
            List of mock NewsItem objects
        """
        mock_data = [
            {
                "title": "以太坊Layer2生态全景分析：从技术原理到赛道格局",
                "content": "本文深入分析了以太坊Layer2扩容方案的技术原理，包括Optimistic Rollups和ZK Rollups的核心差异，以及各大主流项目的技术特点和市场表现。通过对Arbitrum、Optimism、zkSync、StarkNet等项目的详细剖析，帮助读者全面理解Layer2生态的发展现状和未来趋势。",
                "source_url": f"{self.BASE_URL}/post/10000",
                "source_id": "odaily-deep-10000",
            },
            {
                "title": "DeFi协议安全性研究报告：常见漏洞与防范措施",
                "content": "随着DeFi行业的快速发展，协议安全问题日益凸显。本报告系统梳理了DeFi协议中常见的漏洞类型，包括重入攻击、闪电贷攻击、价格操纵等，并结合实际案例分析攻击手段和防范措施，为DeFi开发者和投资者提供参考。",
                "source_url": f"{self.BASE_URL}/post/10001",
                "source_id": "odaily-deep-10001",
            },
            {
                "title": "比特币生态发展路径探讨：从数字黄金到价值互联网",
                "content": "比特币作为加密货币的始祖，其定位和价值不断演进。本文从比特币的技术发展、生态建设、应用场景等多个维度，探讨其从'数字黄金'向'价值互联网基础设施'转型的可能性和路径。",
                "source_url": f"{self.BASE_URL}/post/10002",
                "source_id": "odaily-deep-10002",
            },
            {
                "title": "跨链桥技术深度解析：安全性与去中心化的权衡",
                "content": "跨链桥是连接不同区块链的关键基础设施，但其安全性一直备受争议。本文深入分析了主流跨链桥的技术方案，包括轻客户端验证、中继网络、流动性挖矿等模式，并探讨了如何在安全性和去中心化之间找到平衡点。",
                "source_url": f"{self.BASE_URL}/post/10003",
                "source_id": "odaily-deep-10003",
            },
            {
                "title": "NFT市场低迷下的价值重构：从投机到实用",
                "content": "经历了2022年的泡沫破裂后，NFT市场进入价值重构期。本文分析了NFT从投机工具向实用工具转变的趋势，探讨了NFT在游戏、艺术、身份认证等领域的实际应用价值。",
                "source_url": f"{self.BASE_URL}/post/10004",
                "source_id": "odaily-deep-10004",
            },
            {
                "title": "Web3社交协议的崛起：去中心化身份与数据主权",
                "content": "传统社交平台的数据垄断和审查问题催生了Web3社交协议的兴起。本文介绍了Lens Protocol、Farcaster等主流Web3社交协议的技术架构和生态发展，探讨了去中心化社交的未来可能性。",
                "source_url": f"{self.BASE_URL}/post/10005",
                "source_id": "odaily-deep-10005",
            },
            {
                "title": "模块化区块链架构解析：Celestia与数据可用性采样",
                "content": "模块化区块链是区块链架构的重要创新方向。本文深入介绍了模块化区块链的设计理念，重点分析了Celestia等数据可用性层项目的技术特点，探讨了模块化架构对区块链扩展性的影响。",
                "source_url": f"{self.BASE_URL}/post/10006",
                "source_id": "odaily-deep-10006",
            },
            {
                "title": "ZK证明技术在区块链中的应用前景",
                "content": "零知识证明技术是区块链领域的重要研究方向。本文从技术原理出发，介绍了ZK-SNARKs和ZK-STARKs的核心差异，分析了ZK证明在隐私保护、扩容、跨链等场景的应用前景。",
                "source_url": f"{self.BASE_URL}/post/10007",
                "source_id": "odaily-deep-10007",
            },
            {
                "title": "合规稳定币的发展趋势与监管影响",
                "content": "稳定币是加密货币与法币世界的重要桥梁。本文分析了USDC、USDT等主流稳定币的合规进展，探讨了MiCA等监管法规对稳定币行业的影响，展望了合规稳定币的未来发展。",
                "source_url": f"{self.BASE_URL}/post/10008",
                "source_id": "odaily-deep-10008",
            },
            {
                "title": "RWA代币化：传统金融进入Web3的入口",
                "content": "现实世界资产(RWA)代币化被认为是传统金融进入Web3的重要途径。本文分析了债券、房地产、大宗商品等传统资产的代币化实践，探讨了RWA赛道的发展机遇和挑战。",
                "source_url": f"{self.BASE_URL}/post/10009",
                "source_id": "odaily-deep-10009",
            },
            {
                "title": "MPC钱包技术：安全性与用户体验的平衡",
                "content": "多方计算(MPC)钱包技术被认为是提升加密货币安全性和用户体验的重要方案。本文介绍了MPC钱包的技术原理，对比了传统私钥钱包和MPC钱包的差异，分析了MPC技术在托管和自托管场景的应用。",
                "source_url": f"{self.BASE_URL}/post/10010",
                "source_id": "odaily-deep-10010",
            },
            {
                "title": "GameFi经济模型设计：可持续发展路径",
                "content": "GameFi项目的可持续性一直备受质疑。本文分析了Axie Infinity、StepN等典型案例的经济模型设计问题，探讨了如何在游戏乐趣和经济激励之间找到平衡点，实现GameFi项目的可持续发展。",
                "source_url": f"{self.BASE_URL}/post/10011",
                "source_id": "odaily-deep-10011",
            },
        ]

        items = []
        now = datetime.now()

        for i, data in enumerate(mock_data[:limit]):
            # Simulate decreasing publish time (days ago)
            published_at = datetime.fromtimestamp(now.timestamp() - i * 86400)

            items.append(
                NewsItem(
                    title=data["title"],
                    content=data["content"],
                    source_url=data["source_url"],
                    source_id=data["source_id"],
                    published_at=published_at,
                )
            )

        return items
