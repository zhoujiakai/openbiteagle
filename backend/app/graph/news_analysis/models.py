"""Pydantic models for LLM structured output.

These models define the expected output format from LLM calls,
ensuring consistent and parseable responses.
"""

from typing import Literal

from pydantic import BaseModel, Field


class InvestmentValueOutput(BaseModel):
    """Investment value judgment output.

    The LLM analyzes a news item and determines if it has investment value,
    classifying it as bullish, bearish, or neutral with a confidence score.
    """

    value: Literal["bullish", "bearish", "neutral"] = Field(
        description="Investment value: bullish (positive), bearish (negative), or neutral (no value)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0"
    )
    reasoning: str = Field(description="Brief explanation for the classification")


class TokenInfo(BaseModel):
    """Single token information extracted from news."""

    symbol: str = Field(description="Token symbol (e.g., BTC, ETH)")
    name: str = Field(description="Token full name (e.g., Bitcoin, Ethereum)")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence that this token is relevant"
    )


class TokenExtractionOutput(BaseModel):
    """Token extraction output.

    The LLM identifies cryptocurrency tokens mentioned in the news item.
    """

    tokens: list[TokenInfo] = Field(default_factory=list, description="List of extracted tokens")


class RecommendationOutput(BaseModel):
    """Trading recommendation output.

    The LLM generates a final trading recommendation based on all analysis.
    """

    action: Literal["buy", "sell", "hold"] = Field(
        description="Trading recommendation: buy, sell, or hold"
    )
    reasoning: str = Field(description="Brief explanation for the recommendation")
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Risk level of this trade"
    )
