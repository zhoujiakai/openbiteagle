"""新闻分析图节点的单元测试。

使用模拟的 LLM 响应逐个测试每个节点。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tasks.task2_analyze_flow.models import (
    InvestmentValueOutput,
    RecommendationOutput,
    TokenExtractionOutput,
)
from tasks.task2_analyze_flow.nodes import (
    extract_tokens_node,
    generate_recommendation_node,
    investment_value_node,
    search_token_info_node,
    should_continue_route,
    trend_analysis_node,
)
from tasks.task2_analyze_flow.state import GraphState


def make_mock_llm_structured(output: any):
    """创建带有结构化输出的模拟 LLM。

    节点代码调用: call_llm_structured(llm, prompt, Model, schema)
    因此我们需要直接修补 call_llm_structured。
    """
    async def mock_call(llm, prompt, model_class, schema=None):
        return output
    return mock_call


def make_mock_llm_plain(output: any):
    """创建用于普通 invoke 调用的模拟 LLM。"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = output
    mock_invoke = AsyncMock(return_value=mock_response)
    mock_llm.ainvoke = mock_invoke
    return mock_llm


@pytest.fixture
def sample_state():
    """用于测试的示例图状态。"""
    return {
        "news_id": 1,
        "title": "比特币突破历史新高",
        "content": "比特币已达到 $100,000 的新纪录价格...",
        "investment_value": None,
        "investment_confidence": None,
        "investment_reasoning": None,
        "tokens": None,
        "token_details": None,
        "trend_analysis": None,
        "recommendation": None,
        "risk_level": None,
        "recommendation_reasoning": None,
        "should_continue": True,
        "error": None,
    }


class TestInvestmentValueNode:
    """投资价值节点测试。"""

    @pytest.mark.asyncio
    async def test_bullish_classification(self, sample_state):
        """测试节点正确分类利好新闻。"""
        mock_output = InvestmentValueOutput(
            value="bullish", confidence=0.85, reasoning="强劲的正向动能"
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("tasks.task2_analyze_flow.nodes.call_llm_structured", side_effect=mock_call):
            result = await investment_value_node(sample_state)

        assert result["investment_value"] == "bullish"
        assert result["investment_confidence"] == 0.85
        assert result["should_continue"] is True

    @pytest.mark.asyncio
    async def test_neutral_skip(self, sample_state):
        """测试节点对中性新闻设置 should_continue=False。"""
        mock_output = InvestmentValueOutput(
            value="neutral", confidence=0.3, reasoning="无明显信号"
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("tasks.task2_analyze_flow.nodes.call_llm_structured", side_effect=mock_call):
            result = await investment_value_node(sample_state)

        assert result["investment_value"] == "neutral"
        assert result["should_continue"] is False


class TestExtractTokensNode:
    """代币提取节点测试。"""

    @pytest.mark.asyncio
    async def test_token_extraction(self, sample_state):
        """测试节点从新闻中提取代币。"""
        mock_output = TokenExtractionOutput(
            tokens=[
                {"symbol": "BTC", "name": "Bitcoin", "confidence": 0.95},
                {"symbol": "ETH", "name": "Ethereum", "confidence": 0.7},
            ]
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("tasks.task2_analyze_flow.nodes.call_llm_structured", side_effect=mock_call):
            result = await extract_tokens_node(sample_state)

        assert len(result["tokens"]) == 2
        assert result["tokens"][0]["symbol"] == "BTC"


class TestSearchTokenInfoNode:
    """代币信息搜索节点测试。"""

    @pytest.mark.asyncio
    async def test_token_info_retrieval(self, sample_state):
        """测试节点获取代币市场数据。"""
        sample_state["tokens"] = [
            {"symbol": "BTC", "name": "Bitcoin", "confidence": 0.95}
        ]

        # 在源模块处修补 CMCClient
        with patch("app.wrappers.cmc.CMCClient") as mock_cmc_class:
            mock_cmc_instance = MagicMock()
            mock_cmc_instance.get_token_info = AsyncMock(
                return_value={
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "price": 100000.0,
                    "market_cap": 2000000000000,
                    "change_24h": 5.2,
                }
            )
            mock_cmc_class.return_value = mock_cmc_instance
            result = await search_token_info_node(sample_state)

        assert "BTC" in result["token_details"]
        assert result["token_details"]["BTC"]["price"] == 100000.0


class TestTrendAnalysisNode:
    """趋势分析节点测试。"""

    @pytest.mark.asyncio
    async def test_trend_analysis(self, sample_state):
        """测试节点生成趋势分析。"""
        sample_state["investment_value"] = "bullish"
        sample_state["investment_confidence"] = 0.8
        sample_state["token_details"] = {
            "BTC": {
                "price": 100000.0,
                "market_cap": 2000000000000,
                "change_24h": 5.2,
            }
        }

        mock_response = MagicMock()
        mock_response.content = "强劲的看涨趋势，日涨幅 5%..."
        mock_llm = make_mock_llm_plain(mock_response.content)

        with patch("tasks.task2_analyze_flow.nodes.get_llm", return_value=mock_llm):
            result = await trend_analysis_node(sample_state)

        assert "bullish" in result["trend_analysis"].lower()


class TestGenerateRecommendationNode:
    """推荐生成节点测试。"""

    @pytest.mark.asyncio
    async def test_buy_recommendation(self, sample_state):
        """测试节点生成买入推荐。"""
        sample_state["should_continue"] = True
        sample_state["investment_value"] = "bullish"
        sample_state["investment_confidence"] = 0.8
        sample_state["trend_analysis"] = "强劲的看涨动能..."

        mock_output = RecommendationOutput(
            action="buy", risk_level="medium", reasoning="正向动能已确认"
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("tasks.task2_analyze_flow.nodes.call_llm_structured", side_effect=mock_call):
            result = await generate_recommendation_node(sample_state)

        assert result["recommendation"] == "buy"
        assert result["risk_level"] == "medium"

    @pytest.mark.asyncio
    async def test_skip_to_hold(self, sample_state):
        """测试跳过分析时节点输出 'hold'。"""
        sample_state["should_continue"] = False

        mock_output = RecommendationOutput(
            action="hold", risk_level="low", reasoning="无明显投资价值"
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("tasks.task2_analyze_flow.nodes.call_llm_structured", side_effect=mock_call):
            result = await generate_recommendation_node(sample_state)

        assert result["recommendation"] == "hold"


class TestRouting:
    """路由逻辑测试。"""

    def test_continue_route(self, sample_state):
        """测试路由器对利好新闻返回 'continue'。"""
        sample_state["should_continue"] = True
        assert should_continue_route(sample_state) == "continue"

    def test_skip_route(self, sample_state):
        """测试路由器对中性新闻返回 'skip'。"""
        sample_state["should_continue"] = False
        assert should_continue_route(sample_state) == "skip"
