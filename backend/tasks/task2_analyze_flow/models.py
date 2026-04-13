"""LLM 结构化输出的 Pydantic 模型。

这些模型定义了 LLM 调用的预期输出格式，
确保响应一致且可解析。
"""

from typing import Literal

from pydantic import BaseModel, Field


class InvestmentValueOutput(BaseModel):
    """投资价值判断输出。

    LLM 分析新闻条目并判断其是否具有投资价值，
    分类为利好、利空或中性，并附带置信度评分。
    """

    value: Literal["bullish", "bearish", "neutral"] = Field(
        description="投资价值：bullish（利好）、bearish（利空）或 neutral（中性/无价值）"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="置信度评分，范围 0.0 到 1.0"
    )
    reasoning: str = Field(description="分类的简要说明")


class TokenInfo(BaseModel):
    """从新闻中提取的单个代币信息。"""

    symbol: str = Field(description="代币符号（如 BTC、ETH）")
    name: str = Field(description="代币全名（如 Bitcoin、Ethereum）")
    confidence: float = Field(
        ge=0.0, le=1.0, description="该代币相关性的置信度"
    )


class TokenExtractionOutput(BaseModel):
    """代币提取输出。

    LLM 识别新闻条目中提到的加密货币代币。
    """

    tokens: list[TokenInfo] = Field(default_factory=list, description="提取到的代币列表")


class RecommendationOutput(BaseModel):
    """交易建议输出。

    LLM 基于所有分析生成最终交易建议。
    """

    action: Literal["buy", "sell", "hold"] = Field(
        description="交易建议：buy（买入）、sell（卖出）或 hold（观望）"
    )
    reasoning: str = Field(description="建议的简要说明")
    risk_level: Literal["low", "medium", "high"] = Field(
        description="此交易的风险等级"
    )
