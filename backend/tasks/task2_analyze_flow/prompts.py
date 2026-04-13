"""Prompt templates for news analysis nodes.

Each prompt is designed to elicit specific, structured output from the LLM.
"""

# Investment value judgment prompt
INVESTMENT_VALUE_PROMPT = """You are a Web3 investment analyst. Analyze the following news item and determine its investment value.

## News Item
Title: {title}
Content: {content}

## Analysis Dimensions

1. **Token/Project Specificity**: Does the news mention specific cryptocurrencies or projects?

2. **Market Impact**: Is there substantive positive or negative information that could affect prices?

3. **Information Quality**: Is the source reliable? Is the information verifiable?

4. **Market Attention**: Is this likely to generate significant market interest or trading volume?

## Your Task

Classify the investment value and provide your reasoning:
- **bullish**: Positive information that suggests price increase potential
- **bearish**: Negative information that suggests price decrease potential
- **neutral**: No clear investment value, generic information, or insufficient data

Provide:
1. Classification (bullish/bearish/neutral)
2. Confidence (0.0-1.0)
3. Brief reasoning (1-2 sentences)
"""

# Token extraction prompt
TOKEN_EXTRACTION_PROMPT = """You are a cryptocurrency expert. Extract all relevant cryptocurrency tokens mentioned in the news.

## News Item
Title: {title}
Content: {content}

## Your Task

Identify all cryptocurrencies mentioned that are:
- Actively traded on major exchanges
- Have meaningful market cap/liquidity
- Are directly relevant to the news content

For each token, provide:
1. **symbol**: Trading symbol (e.g., BTC, ETH, SOL)
2. **name**: Full name (e.g., Bitcoin, Ethereum, Solana)
3. **confidence**: How relevant this token is to the main story (0.0-1.0)

Exclude:
- Dead/abandoned projects
- Tokens mentioned only in passing without relevance
- Generic references not tied to specific projects

If no relevant tokens are found, return an empty list.
"""

# Trend analysis prompt (original, without RAG)
TREND_ANALYSIS_PROMPT = """You are a Web3 market analyst. Analyze the trend implications of this news.

## News Item
Title: {title}
Content: {content}

## Investment Value Assessment
Classification: {investment_value}
Confidence: {confidence}

## Token Market Data
{token_data}

## Your Task

Analyze the potential price trend impact:
1. **Short-term direction**: Immediate market reaction expected
2. **Key factors**: What specifically will drive price movement
3. **Risk considerations**: What could reverse this trend
4. **Timeframe**: How long the impact might last

Provide a concise trend analysis (2-3 sentences).
"""

# Trend analysis prompt with RAG enhancement
TREND_ANALYSIS_WITH_RAG_PROMPT = """You are a Web3 market analyst with access to a knowledge base. Analyze the trend implications of this news.

## News Item
Title: {title}
Content: {content}

## Investment Value Assessment
Classification: {investment_value}
Confidence: {confidence}

## Token Market Data
{token_data}

## Knowledge Base Context
{rag_context}

## Your Task

Analyze the potential price trend impact using both the news and knowledge base information:
1. **Short-term direction**: Immediate market reaction expected
2. **Key factors**: What specifically will drive price movement (incorporate KB insights)
3. **Risk considerations**: What could reverse this trend (consider project fundamentals from KB)
4. **Timeframe**: How long the impact might last

Provide a concise trend analysis (2-3 sentences) that leverages the knowledge base for deeper insight.
"""

# Recommendation prompt
RECOMMENDATION_PROMPT = """You are a conservative trading advisor. Generate a recommendation based on the analysis.

## Analysis Summary

**News**: {title}

**Investment Value**: {investment_value} (confidence: {confidence})

**Trend Analysis**: {trend_analysis}

## Your Task

Generate a trading recommendation:
- **buy**: Strong positive signal with acceptable risk
- **sell**: Strong negative signal with acceptable risk
- **hold**: Uncertain, neutral, or risk too high

Also assess risk level:
- **low**: Established token, clear catalyst, low uncertainty
- **medium**: Newer token or moderate uncertainty
- **high**: Highly speculative, low liquidity, or extreme uncertainty

Provide:
1. Action (buy/sell/hold)
2. Risk level
3. Brief reasoning
"""

# Neutral fallback prompt (when no investment value)
NEUTRAL_RECOMMENDATION_PROMPT = """You are a conservative trading advisor.

The news item was analyzed and classified as having no significant investment value (neutral).

## News Item
Title: {title}
Content: {content}

## Your Task

Since there is no clear investment value or actionable signal, recommend "hold" with low risk.

Provide brief reasoning explaining why this news doesn't warrant action.
"""

# Route check prompt (optional, for more nuanced routing)
ROUTE_CHECK_PROMPT = """Determine if this news justifies a full token analysis.

Classification: {investment_value}
Confidence: {confidence}

For "neutral" with confidence < 0.5: Skip token analysis, go directly to hold recommendation.
Otherwise: Continue with full analysis pipeline.
"""


def format_investment_value_prompt(title: str, content: str) -> str:
    """Format the investment value judgment prompt."""
    return INVESTMENT_VALUE_PROMPT.format(title=title, content=content or "")


def format_token_extraction_prompt(title: str, content: str) -> str:
    """Format the token extraction prompt."""
    return TOKEN_EXTRACTION_PROMPT.format(title=title, content=content or "")


def format_trend_analysis_prompt(
    title: str,
    content: str,
    investment_value: str,
    confidence: float,
    token_data: str,
    rag_context: str | None = None,
) -> str:
    """Format the trend analysis prompt."""
    if rag_context:
        return TREND_ANALYSIS_WITH_RAG_PROMPT.format(
            title=title,
            content=content or "",
            investment_value=investment_value,
            confidence=confidence,
            token_data=token_data or "No token data available",
            rag_context=rag_context or "No additional context available",
        )
    return TREND_ANALYSIS_PROMPT.format(
        title=title,
        content=content or "",
        investment_value=investment_value,
        confidence=confidence,
        token_data=token_data or "No token data available",
    )


def format_recommendation_prompt(
    title: str,
    investment_value: str,
    confidence: float,
    trend_analysis: str,
) -> str:
    """Format the recommendation prompt."""
    return RECOMMENDATION_PROMPT.format(
        title=title,
        investment_value=investment_value,
        confidence=confidence,
        trend_analysis=trend_analysis or "No trend analysis available",
    )


def format_neutral_recommendation_prompt(title: str, content: str) -> str:
    """Format the neutral (skip) recommendation prompt."""
    return NEUTRAL_RECOMMENDATION_PROMPT.format(title=title, content=content or "")
