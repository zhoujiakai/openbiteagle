"""分析模式。"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class StepResult(BaseModel):
    """单个分析步骤结果的模式。"""

    name: str = Field(..., description="Step/node name")
    result: Optional[dict[str, Any]] = Field(None, description="Step execution result")
    error: Optional[str] = Field(None, description="Error message if step failed")


class AnalysisCreate(BaseModel):
    """创建分析请求的模式。"""

    news_id: Optional[int] = Field(None, gt=0, description="Existing news ID")
    news_content: Optional[str] = Field(None, min_length=1, description="Raw news content")

    def has_content(self) -> bool:
        """检查请求是否包含有效的内容来源。"""
        return self.news_id is not None or self.news_content is not None


class BatchAnalysisCreate(BaseModel):
    """批量分析请求的模式。"""

    news_ids: list[int] = Field(..., min_length=1, max_length=50, description="List of news IDs")


class AnalysisBase(BaseModel):
    """分析基础模式。"""

    news_id: int = Field(..., gt=0)
    investment_value: Optional[str] = Field(None, pattern="^(bullish|bearish|neutral)$")
    confidence: Optional[Decimal] = Field(None, ge=0, le=1)
    tokens: Optional[list[dict]] = None
    trend_analysis: Optional[str] = None
    recommendation: Optional[str] = Field(None, pattern="^(buy|sell|hold)$")


class AnalysisResponse(AnalysisBase):
    """分析响应模式。"""

    id: int
    status: str
    langsmith_trace: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenInfo(BaseModel):
    """代币信息模式。"""

    symbol: str
    name: Optional[str] = None
    recommendation: Optional[str] = None
    reasoning: Optional[str] = None


class InvestmentValueResult(BaseModel):
    """投资价值判断结果。"""

    value: str = Field(..., pattern="^(bullish|bearish|neutral)$")
    confidence: Decimal = Field(..., ge=0, le=1)
    reasoning: str


class TokenExtractionResult(BaseModel):
    """代币提取结果。"""

    tokens: list[TokenInfo]
    has_tokens: bool


class TrendAnalysisResult(BaseModel):
    """趋势分析结果。"""

    recommendation: str = Field(..., pattern="^(buy|sell|hold)$")
    analysis: str
    key_factors: list[str]


class AnalysisCreateResponse(BaseModel):
    """分析创建响应模式。"""

    analysis_id: int
    news_id: int
    status: str = Field(..., description="Initial status (pending/processing)")


class AnalysisDetail(AnalysisBase):
    """详细分析响应模式。"""

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
    """批量分析响应模式。"""

    analysis_ids: list[int]
    count: int
    status: str = "pending"


class TokenCount(BaseModel):
    """代币计数统计模式。"""

    symbol: str
    count: int


class AnalysisOverview(BaseModel):
    """分析概览/统计模式。"""

    total: int = Field(..., description="Total number of analyses")
    by_value: dict[str, int] = Field(default_factory=dict, description="Count by investment value")
    top_tokens: list[TokenCount] = Field(default_factory=list, description="Most mentioned tokens")
    recommendations: dict[str, int] = Field(default_factory=dict, description="Count by recommendation")
