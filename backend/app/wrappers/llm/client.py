"""LLM client wrapper for unified LLM access.

Provides a unified interface for using different LLM providers
(DeepSeek, OpenAI, etc.) with structured output support.
"""

import json
import logging
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_llm(
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> ChatOpenAI:
    """Get configured LLM instance.

    Priority: DeepSeek (primary, low cost) → OpenAI (fallback)

    Args:
        model: Override model name
        temperature: LLM temperature

    Returns:
        ChatOpenAI instance
    """
    # Try DeepSeek first
    if settings.DEEPSEEK_API_KEY:
        return ChatOpenAI(
            model=model or settings.DEEPSEEK_MODEL or "deepseek-chat",
            temperature=temperature,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com",
        )

    # Fallback to OpenAI
    return ChatOpenAI(
        model=model or settings.OPENAI_MODEL or "gpt-4o-mini",
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
    )


def is_using_deepseek() -> bool:
    """Check if DeepSeek is configured and will be used.

    Returns:
        True if DeepSeek API key is set
    """
    return bool(settings.DEEPSEEK_API_KEY)


async def call_llm_structured(
    llm: ChatOpenAI,
    prompt: str,
    model_class: type,
    schema: Optional[dict] = None,
) -> Any:
    """Call LLM with structured output, handling DeepSeek compatibility.

    Args:
        llm: LLM instance
        prompt: The prompt to send
        model_class: Pydantic model class for parsing
        schema: Optional JSON schema for DeepSeek

    Returns:
        Instance of model_class
    """
    is_deepseek = is_using_deepseek()

    if is_deepseek:
        # DeepSeek doesn't support structured_output, use JSON mode with prompt
        json_schema = json.dumps(schema or {"type": "object"}, indent=2)

        enhanced_prompt = f"""{prompt}

IMPORTANT: You must respond with a valid JSON object following this schema:
{json_schema}

Respond ONLY with the JSON object, no additional text."""

        content = ""
        try:
            response = await llm.ainvoke([HumanMessage(content=enhanced_prompt)])
            content = response.content.strip() if hasattr(response, "content") else str(response)

            # Try to parse as JSON
            if isinstance(content, str):
                # Remove markdown code blocks if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

                # Remove trailing ``` if present
                if content.endswith("```"):
                    content = content[:-3].strip()

            data = json.loads(content) if isinstance(content, str) else content
            return model_class(**data)

        except (json.JSONDecodeError, TypeError, Exception) as e:
            logger.warning(f"Failed to parse DeepSeek JSON response: {e}, content: {content[:200] if content else 'empty'}")
            # Return default instance
            return model_class.model_construct()

    else:
        # OpenAI supports structured_output
        response = await llm.with_structured_output(model_class).ainvoke(
            [HumanMessage(content=prompt)]
        )
        return response
