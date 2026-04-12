"""新闻爬取封装模块。

本模块提供解耦的新闻爬取接口，
允许添加不同的新闻源而无需修改业务逻辑层。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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


@dataclass
class ContentResult:
    """详情页内容提取结果。"""

    text: Optional[str] = None
    html: Optional[str] = None
    images: list[ImageInfo] = field(default_factory=list)

    @property
    def has_content(self) -> bool:
        """检查内容是否成功提取。"""
        return bool(self.text)


class BaseNewsScraper(ABC):
    """新闻爬虫抽象基类。

    所有新闻源爬虫都应继承此类并实现所需的方法。
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """返回新闻源名称。"""

    @abstractmethod
    async def fetch_news(self, limit: int = 50) -> list[NewsItem]:
        """获取新闻条目列表。

        Args:
            limit: 最大获取数量

        Returns:
            NewsItem 对象列表
        """

    @abstractmethod
    async def fetch_news_detail(self, news_id: str) -> Optional[NewsItem]:
        """根据 ID 获取单条新闻。

        Args:
            news_id: 新闻条目的唯一标识符

        Returns:
            NewsItem 对象，未找到时返回 None
        """

    async def health_check(self) -> bool:
        """检查爬虫是否能连接到新闻源。

        Returns:
            连接成功返回 True，否则返回 False
        """
        try:
            items = await self.fetch_news(limit=1)
            return len(items) >= 0
        except Exception:
            return False
