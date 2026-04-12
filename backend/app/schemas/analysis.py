"""Analysis schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class StepResult(BaseModel):
    """Schema for a single analysis step result."""

    name: str = Field(..., description="Step/node name")
    result: Optional[dict[str, Any]] = Field(None, description="Step execution result")
    error: Optional[str] = Field(None, description="Error message if step failed")


class AnalysisCreate(BaseModel):
    """Schema for creating analysis request."""

    news_id: Optional[int] = Field(None, gt=0, description="Existing news ID")
    news_content: Optional[str] = Field(None, min_length=1, description="Raw news content")

    def has_content(self) -> bool:
        """Check if request has valid content source."""
        return self.news_id is not None or self.news_content is not None


class BatchAnalysisCreate(BaseModel):
    """Schema for batch analysis request."""

    news_ids: list[int] = Field(..., min_length=1, max_length=50, description="List of news IDs")


class AnalysisBase(BaseModel):
    """Base analysis schema."""

    news_id: int = Field(..., gt=0)
    investment_value: Optional[str] = Field(None, pattern="^(bullish|bearish|neutral)$")
    confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    tokens: Optional[list[dict]] = None
    trend_analysis: Optional[str] = None
    recommendation: Optional[str] = Field(None, pattern="^(buy|sell|hold)$")


class AnalysisResponse(AnalysisBase):
    """Schema for analysis response."""

    id: int
    status: str
    langsmith_trace: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenInfo(BaseModel):
    """Token information schema."""

    symbol: str
    name: Optional[str] = None
    recommendation: Optional[str] = None
    reasoning: Optional[str] = None


class InvestmentValueResult(BaseModel):
    """Investment value judgment result."""

    value: str = Field(..., pattern="^(bullish|bearish|neutral)$")
    confidence: Decimal = Field(..., ge=0, le=1)
    reasoning: str


class TokenExtractionResult(BaseModel):
    """Token extraction result."""

    tokens: list[TokenInfo]
    has_tokens: bool


class TrendAnalysisResult(BaseModel):
    """Trend analysis result."""

    recommendation: str = Field(..., pattern="^(buy|sell|hold)$")
    analysis: str
    key_factors: list[str]


class AnalysisCreateResponse(BaseModel):
    """Schema for analysis creation response."""

    analysis_id: int
    status: str = Field(..., description="Initial status (pending/processing)")


class AnalysisDetail(AnalysisBase):
    """Schema for detailed analysis response."""

    id: int
    status: str
    steps: Optional[list[StepResult]] = None
    langsmith_trace: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchAnalysisResponse(BaseModel):
    """Schema for batch analysis response."""

    analysis_ids: list[int]
    count: int
    status: str = "pending"


class TokenCount(BaseModel):
    """Schema for token count statistics."""

    symbol: str
    count: int


class AnalysisOverview(BaseModel):
    """Schema for analysis overview/statistics."""

    total: int = Field(..., description="Total number of analyses")
    by_value: dict[str, int] = Field(default_factory=dict, description="Count by investment value")
    top_tokens: list[TokenCount] = Field(default_factory=list, description="Most mentioned tokens")
    recommendations: dict[str, int] = Field(default_factory=dict, description="Count by recommendation")
