"""Unit tests for news analysis graph nodes.

Tests each node in isolation with mocked LLM responses.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.graph.news_analysis.models import (
    InvestmentValueOutput,
    RecommendationOutput,
    TokenExtractionOutput,
)
from app.graph.news_analysis.nodes import (
    extract_tokens_node,
    generate_recommendation_node,
    investment_value_node,
    search_token_info_node,
    should_continue_route,
    trend_analysis_node,
)
from app.graph.news_analysis.state import GraphState


def make_mock_llm_structured(output: any):
    """Create a mock LLM with structured output.

    The node code does: call_llm_structured(llm, prompt, Model, schema)
    So we need to patch call_llm_structured directly.
    """
    async def mock_call(llm, prompt, model_class, schema=None):
        return output
    return mock_call


def make_mock_llm_plain(output: any):
    """Create a mock LLM for plain invoke calls."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = output
    mock_invoke = AsyncMock(return_value=mock_response)
    mock_llm.ainvoke = mock_invoke
    return mock_llm


@pytest.fixture
def sample_state():
    """Sample graph state for testing."""
    return {
        "news_id": 1,
        "title": "Bitcoin breaks new all-time high",
        "content": "Bitcoin has reached a new record price of $100,000...",
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
    """Tests for investment_value_node."""

    @pytest.mark.asyncio
    async def test_bullish_classification(self, sample_state):
        """Test node correctly classifies bullish news."""
        mock_output = InvestmentValueOutput(
            value="bullish", confidence=0.85, reasoning="Strong positive momentum"
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("app.graph.news_analysis.nodes.call_llm_structured", side_effect=mock_call):
            result = await investment_value_node(sample_state)

        assert result["investment_value"] == "bullish"
        assert result["investment_confidence"] == 0.85
        assert result["should_continue"] is True

    @pytest.mark.asyncio
    async def test_neutral_skip(self, sample_state):
        """Test node sets should_continue=False for neutral news."""
        mock_output = InvestmentValueOutput(
            value="neutral", confidence=0.3, reasoning="No clear signal"
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("app.graph.news_analysis.nodes.call_llm_structured", side_effect=mock_call):
            result = await investment_value_node(sample_state)

        assert result["investment_value"] == "neutral"
        assert result["should_continue"] is False


class TestExtractTokensNode:
    """Tests for extract_tokens_node."""

    @pytest.mark.asyncio
    async def test_token_extraction(self, sample_state):
        """Test node extracts tokens from news."""
        mock_output = TokenExtractionOutput(
            tokens=[
                {"symbol": "BTC", "name": "Bitcoin", "confidence": 0.95},
                {"symbol": "ETH", "name": "Ethereum", "confidence": 0.7},
            ]
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("app.graph.news_analysis.nodes.call_llm_structured", side_effect=mock_call):
            result = await extract_tokens_node(sample_state)

        assert len(result["tokens"]) == 2
        assert result["tokens"][0]["symbol"] == "BTC"


class TestSearchTokenInfoNode:
    """Tests for search_token_info_node."""

    @pytest.mark.asyncio
    async def test_token_info_retrieval(self, sample_state):
        """Test node fetches market data for tokens."""
        sample_state["tokens"] = [
            {"symbol": "BTC", "name": "Bitcoin", "confidence": 0.95}
        ]

        # Patch CMCClient at its source module
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
    """Tests for trend_analysis_node."""

    @pytest.mark.asyncio
    async def test_trend_analysis(self, sample_state):
        """Test node generates trend analysis."""
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
        mock_response.content = "Strong bullish trend with 5% daily gain..."
        mock_llm = make_mock_llm_plain(mock_response.content)

        with patch("app.graph.news_analysis.nodes.get_llm", return_value=mock_llm):
            result = await trend_analysis_node(sample_state)

        assert "bullish" in result["trend_analysis"].lower()


class TestGenerateRecommendationNode:
    """Tests for generate_recommendation_node."""

    @pytest.mark.asyncio
    async def test_buy_recommendation(self, sample_state):
        """Test node generates buy recommendation."""
        sample_state["should_continue"] = True
        sample_state["investment_value"] = "bullish"
        sample_state["investment_confidence"] = 0.8
        sample_state["trend_analysis"] = "Strong bullish momentum..."

        mock_output = RecommendationOutput(
            action="buy", risk_level="medium", reasoning="Positive momentum confirmed"
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("app.graph.news_analysis.nodes.call_llm_structured", side_effect=mock_call):
            result = await generate_recommendation_node(sample_state)

        assert result["recommendation"] == "buy"
        assert result["risk_level"] == "medium"

    @pytest.mark.asyncio
    async def test_skip_to_hold(self, sample_state):
        """Test node outputs 'hold' when skipping analysis."""
        sample_state["should_continue"] = False

        mock_output = RecommendationOutput(
            action="hold", risk_level="low", reasoning="No significant value"
        )
        mock_call = make_mock_llm_structured(mock_output)

        with patch("app.graph.news_analysis.nodes.call_llm_structured", side_effect=mock_call):
            result = await generate_recommendation_node(sample_state)

        assert result["recommendation"] == "hold"


class TestRouting:
    """Tests for routing logic."""

    def test_continue_route(self, sample_state):
        """Test router returns 'continue' for bullish news."""
        sample_state["should_continue"] = True
        assert should_continue_route(sample_state) == "continue"

    def test_skip_route(self, sample_state):
        """Test router returns 'skip' for neutral news."""
        sample_state["should_continue"] = False
        assert should_continue_route(sample_state) == "skip"
