"""基于 Odaily REST API 的新闻抓取器。

接口文档: https://github.com/ODAILY/REST-API
Base URL: https://api.odaily.news
"""

import asyncio
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.data.logger import create_logger

logger = create_logger("Odaily REST API")

BASE_URL = "https://api.odaily.news"

# 快讯分类端点（均支持 page / size / lang 参数）
NEWSFLASH_ENDPOINTS: dict[str, str] = {
    "全部快讯": "/api/v1/newsflash",
    "24h快讯": "/api/v1/newsflash/24h",
    "24h热门快讯": "/api/v1/newsflash/24h-hot",
    "AI快讯": "/api/v1/newsflash/ai",
    "预测市场": "/api/v1/newsflash/prediction-market",
    "链上数据": "/api/v1/newsflash/on-chain-data",
    "行情播报": "/api/v1/newsflash/market-report",
    "交易所公告": "/api/v1/newsflash/exchange-announcement",
    "项目动向": "/api/v1/newsflash/project-trend",
    "名人观点": "/api/v1/newsflash/celebrity-opinion",
    "币股动态": "/api/v1/newsflash/crypto-stock",
    "融资信息": "/api/v1/newsflash/funding",
    "宏观政策": "/api/v1/newsflash/macro-policy",
}

# 文章端点
ARTICLE_ENDPOINTS: dict[str, str] = {
    "全部文章": "/api/v1/article",
    "24h文章": "/api/v1/article/24h",
    "24h热门文章": "/api/v1/article/24h-hot",
    "深度文章": "/api/v1/article/depth",
    "重要文章": "/api/v1/article/important",
}


@dataclass
class NewsItem:
    """新闻条目数据结构。"""

    id: Optional[str] = None
    title: str = ""
    content: Optional[str] = None
    images: Optional[list[str]] = None
    isImportant: bool = False
    publishTimestamp: Optional[int] = None
    publishDate: Optional[str] = None
    sourceUrl: Optional[str] = None
    link: Optional[str] = None

    def to_dict(self) -> dict:
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


class OdailyRestScraper:
    """基于 Odaily 公开 REST API 的新闻抓取器。

    不需要认证，直接通过 HTTP GET 请求获取数据。
    """

    def __init__(self, lang: str = "zh-cn", timeout: float = 15.0):
        """初始化。

        Args:
            lang: 语言，默认 zh-cn
            timeout: HTTP 请求超时秒数
        """
        self.lang = lang
        self.timeout = timeout

    @property
    def source_name(self) -> str:
        return "Odaily.REST"

    # ── 快讯接口 ──────────────────────────────────────────

    async def fetch_news(
        self,
        limit: int,
        endpoint: str = "/api/v1/newsflash",
        isImportant: Optional[bool] = None,
    ) -> list[NewsItem]:
        """获取快讯列表。

        Args:
            limit: 最大获取数量
            endpoint: 快讯端点路径，默认全部快讯
            isImportant: 是否只获取重要快讯（仅 /api/v1/newsflash 支持）

        Returns:
            NewsItem 列表
        """
        return await self._fetch_paginated(
            endpoint=endpoint,
            limit=limit,
            extra_params={"isImportant": isImportant} if isImportant else None,
        )

    async def fetch_24h_news(self, limit: int = 20) -> list[NewsItem]:
        """获取最近 24 小时快讯。"""
        return await self.fetch_news(limit=limit, endpoint="/api/v1/newsflash/24h")

    async def fetch_24h_hot_news(self, limit: int = 20) -> list[NewsItem]:
        """获取 24 小时热门快讯。"""
        return await self.fetch_news(limit=limit, endpoint="/api/v1/newsflash/24h-hot")

    # ── 文章接口 ──────────────────────────────────────────

    async def fetch_articles(
        self,
        limit: int,
        endpoint: str = "/api/v1/article",
    ) -> list[NewsItem]:
        """获取文章列表。

        Args:
            limit: 最大获取数量
            endpoint: 文章端点路径，默认全部文章

        Returns:
            NewsItem 列表
        """
        return await self._fetch_paginated(endpoint=endpoint, limit=limit)

    async def fetch_24h_articles(self, limit: int = 20) -> list[NewsItem]:
        """获取最近 24 小时文章。"""
        return await self.fetch_articles(limit=limit, endpoint="/api/v1/article/24h")

    async def fetch_depth_articles(self, limit: int = 20) -> list[NewsItem]:
        """获取深度文章。"""
        return await self.fetch_articles(limit=limit, endpoint="/api/v1/article/depth")

    # ── 搜索接口 ──────────────────────────────────────────

    async def search_newsflash(
        self, keyword: str, limit: int = 20
    ) -> list[NewsItem]:
        """按关键词搜索快讯。

        Args:
            keyword: 搜索关键词
            limit: 最大获取数量
        """
        return await self._fetch_paginated(
            endpoint="/api/v1/search/newsflash",
            limit=limit,
            extra_params={"keyword": keyword},
        )

    async def search_articles(
        self, keyword: str, limit: int = 20
    ) -> list[NewsItem]:
        """按关键词搜索文章。

        Args:
            keyword: 搜索关键词
            limit: 最大获取数量
        """
        return await self._fetch_paginated(
            endpoint="/api/v1/search/article",
            limit=limit,
            extra_params={"keyword": keyword},
        )

    # ── 健康检查 ──────────────────────────────────────────

    async def health_check(self) -> bool:
        """检查 API 是否可达。"""
        try:
            async with httpx.AsyncClient(http2=False, timeout=self.timeout) as client:
                resp = await client.get(
                    f"{BASE_URL}/api/v1/newsflash",
                    params={"page": 1, "size": 1, "lang": self.lang},
                    headers={"Accept": "application/json"},
                )
                data = resp.json()
                return data.get("code") == 200 and data.get("success") is True
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False

    # ── 内部方法 ──────────────────────────────────────────

    async def _fetch_paginated(
        self,
        endpoint: str,
        limit: int,
        extra_params: Optional[dict] = None,
        page_size: int = 20,
    ) -> list[NewsItem]:
        """分页获取数据直到达到 limit。

        Args:
            endpoint: API 端点
            limit: 最大获取数量
            extra_params: 额外查询参数
            page_size: 每页条数
        """
        all_items: list[NewsItem] = []
        page = 1

        async with httpx.AsyncClient(http2=False, timeout=self.timeout) as client:
            while len(all_items) < limit:
                params: dict = {
                    "page": page,
                    "size": min(page_size, limit - len(all_items)),
                    "lang": self.lang,
                }
                if extra_params:
                    params.update(extra_params)

                try:
                    resp = await client.get(
                        f"{BASE_URL}{endpoint}",
                        params=params,
                        headers={"Accept": "application/json"},
                    )
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP 错误 [{endpoint}] page={page}: {e}")
                    break
                except httpx.RequestError as e:
                    logger.error(f"请求失败 [{endpoint}] page={page}: {e}")
                    break

                body = resp.json()
                if body.get("code") != 200 or not body.get("success"):
                    logger.warning(
                        f"API 返回非成功状态 [{endpoint}]: "
                        f"code={body.get('code')} msg={body.get('msg')}"
                    )
                    break

                page_data = body.get("data", {})
                item_list = page_data.get("list", [])

                if not item_list:
                    break

                for raw in item_list:
                    item = self._parse_item(raw)
                    if item:
                        all_items.append(item)

                logger.info(
                    f"[{endpoint}] page={page} "
                    f"本页 {len(item_list)} 条，累计 {len(all_items)} 条"
                )

                # 没有更多数据
                if not page_data.get("hasMore", False):
                    break

                page += 1
                # 避免请求过快
                await asyncio.sleep(0.3)

        logger.info(f"[{endpoint}] 共获取 {len(all_items)} 条")
        return all_items[:limit]

    @staticmethod
    def _parse_item(raw: dict) -> Optional[NewsItem]:
        """将 API 返回的单条数据解析为 NewsItem。"""
        title = raw.get("title", "").strip()
        if not title:
            return None

        # content 去除 HTML 标签和 Odaily 前缀
        content = raw.get("content")
        if content:
            content = re.sub(r"<[^>]+>", "", content).strip()
            content = content.removeprefix("Odaily星球日报讯").strip() or None

        return NewsItem(
            id=str(raw.get("id")) if raw.get("id") else None,
            title=title,
            content=content,
            images=raw.get("images") or None,
            isImportant=bool(raw.get("isImportant", False)),
            publishTimestamp=raw.get("publishTimestamp"),
            publishDate=raw.get("publishDate"),
            sourceUrl=raw.get("sourceUrl") or None,
            link=raw.get("link"),
        )


def main():
    """独立运行：抓取最新快讯并打印。"""
    async def _run():
        scraper = OdailyRestScraper()

        print("=== 健康检查 ===")
        ok = await scraper.health_check()
        print(f"API 可达: {'是' if ok else '否'}\n")

        if not ok:
            return

        print("=== 最新快讯 (前 20 条) ===")
        items = await scraper.fetch_news(limit=100)
        for item in items:
            print(f"[{item.publishDate}] {item.title}")
            if item.content:
                print(f"  {item.content[:80]}...")
            if item.link:
                print(f"  链接: {item.link}")
            print()

        print(f"共 {len(items)} 条\n")

        # 演示搜索
        print("=== 搜索快讯: 比特币 ===")
        results = await scraper.search_newsflash(keyword="比特币", limit=5)
        for item in results:
            print(f"  [{item.publishDate}] {item.title}")
        print(f"共 {len(results)} 条\n")

        # 演示文章
        print("=== 最新文章 (前 5 条) ===")
        articles = await scraper.fetch_articles(limit=5)
        for item in articles:
            print(f"  [{item.publishDate}] {item.title}")
        print(f"共 {len(articles)} 条")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
