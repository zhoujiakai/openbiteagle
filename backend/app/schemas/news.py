"""新闻模式。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NewsBase(BaseModel):
    """新闻基础模式。"""

    title: str = Field(..., min_length=1, max_length=500)
    content: Optional[str] = None
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    published_at: Optional[datetime] = None


class NewsCreate(NewsBase):
    """创建新闻的模式。"""

    pass


class NewsUpdate(BaseModel):
    """更新新闻的模式。"""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    published_at: Optional[datetime] = None


class NewsResponse(NewsBase):
    """新闻响应模式。"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
