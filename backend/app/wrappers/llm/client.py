"""LLM 客户端封装，用于统一的 LLM 访问。

提供统一的接口来使用不同的 LLM 提供商
（DeepSeek、OpenAI 等），支持结构化输出。
"""

import json
import logging
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import cfg

logger = logging.getLogger(__name__)


def get_llm(
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> ChatOpenAI:
    """获取已配置的 LLM 实例。

    优先级：DeepSeek（主要，低成本）→ OpenAI（备用）

    Args:
        model: 覆盖模型名称
        temperature: LLM 温度参数

    Returns:
        ChatOpenAI 实例
    """
    # 优先使用 DeepSeek
    if cfg.deepseek.DEEPSEEK_API_KEY:
        return ChatOpenAI(
            model=model or cfg.deepseek.DEEPSEEK_MODEL or "deepseek-chat",
            temperature=temperature,
            api_key=cfg.deepseek.DEEPSEEK_API_KEY,
            base_url=cfg.deepseek.DEEPSEEK_BASE_URL or "https://api.deepseek.com",
        )

    # 回退到 OpenAI
    return ChatOpenAI(
        model=model or cfg.openai.OPENAI_MODEL or "gpt-4o-mini",
        temperature=temperature,
        api_key=cfg.openai.OPENAI_API_KEY,
    )


def is_using_deepseek() -> bool:
    """检查 DeepSeek 是否已配置并将会被使用。

    Returns:
        如果设置了 DeepSeek API 密钥则返回 True
    """
    return bool(cfg.deepseek.DEEPSEEK_API_KEY)


async def call_llm_structured(
    llm: ChatOpenAI,
    prompt: str,
    model_class: type,
    schema: Optional[dict] = None,
) -> Any:
    """调用 LLM 并获取结构化输出，处理 DeepSeek 兼容性。

    Args:
        llm: LLM 实例
        prompt: 要发送的提示词
        model_class: 用于解析的 Pydantic 模型类
        schema: 可选的 DeepSeek JSON 模式

    Returns:
        model_class 的实例
    """
    is_deepseek = is_using_deepseek()

    if is_deepseek:
        # DeepSeek 不支持 structured_output，使用 JSON 模式配合提示词
        json_schema = json.dumps(schema or {"type": "object"}, indent=2)

        enhanced_prompt = f"""{prompt}

IMPORTANT: You must respond with a valid JSON object following this schema:
{json_schema}

Respond ONLY with the JSON object, no additional text."""

        content = ""
        try:
            response = await llm.ainvoke([HumanMessage(content=enhanced_prompt)])
            content = response.content.strip() if hasattr(response, "content") else str(response)

            # 尝试解析为 JSON
            if isinstance(content, str):
                # 移除可能存在的 markdown 代码块
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

                # 移除末尾的 ```
                if content.endswith("```"):
                    content = content[:-3].strip()

            data = json.loads(content) if isinstance(content, str) else content
            return model_class(**data)

        except (json.JSONDecodeError, TypeError, Exception) as e:
            logger.warning(f"Failed to parse DeepSeek JSON response: {e}, content: {content[:200] if content else 'empty'}")
            # 返回默认实例
            return model_class.model_construct()

    else:
        # OpenAI 支持 structured_output
        response = await llm.with_structured_output(model_class).ainvoke(
            [HumanMessage(content=prompt)]
        )
        return response
