"""News schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NewsBase(BaseModel):
    """Base news schema."""

    title: str = Field(..., min_length=1, max_length=500)
    content: Optional[str] = None
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    published_at: Optional[datetime] = None


class NewsCreate(NewsBase):
    """Schema for creating news."""

    pass


class NewsUpdate(BaseModel):
    """Schema for updating news."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    published_at: Optional[datetime] = None


class NewsResponse(NewsBase):
    """Schema for news response."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
