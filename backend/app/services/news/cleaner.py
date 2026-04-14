"""Data cleaning utilities."""

import html
import re
from typing import Optional

import bleach


def clean_html(html_content: str) -> str:
    """Clean HTML content by removing tags but preserving text.

    Args:
        html_content: Raw HTML content

    Returns:
        Cleaned text content
    """
    if not html_content:
        return ""

    # 移除 script 和 style 元素
    cleaned = re.sub(r"<(script|style).*?>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)

    # 使用 bleach 清理 HTML（移除所有标签）
    cleaned = bleach.clean(cleaned, tags=[], strip=True)

    # 解码 HTML 实体
    cleaned = html.unescape(cleaned)

    return cleaned.strip()


def clean_text(text: str) -> str:
    """Clean text content.

    Args:
        text: Raw text

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # 移除多余空白
    text = re.sub(r"\s+", " ", text)

    # 移除控制字符
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)

    return text.strip()


def clean_title(title: str) -> str:
    """Clean news title.

    Args:
        title: Raw title

    Returns:
        Cleaned title
    """
    if not title:
        return ""

    title = clean_text(title)

    # 移除常见前缀
    prefixes_to_remove = ["【快讯】", "【", "】", "[快讯]", "[", "]"]
    for prefix in prefixes_to_remove:
        if title.startswith(prefix):
            title = title[len(prefix):]
        if title.endswith(prefix):
            title = title[:-len(prefix)]

    return title.strip()


def is_valid_news(title: str, content: Optional[str] = None) -> bool:
    """Check if news item is valid.

    Args:
        title: News title
        content: News content

    Returns:
        True if valid, False otherwise
    """
    if not title or len(title.strip()) < 5:
        return False

    # 检查垃圾/无效内容模式
    spam_patterns = [
        r"^test\s*$",
        r"^测试\s*$",
        r"^(advertisement|广告)\s*$",
    ]

    combined_text = f"{title} {content or ''}".lower()
    for pattern in spam_patterns:
        if re.match(pattern, combined_text, re.IGNORECASE):
            return False

    return True


def extract_tokens_from_text(text: str) -> list[str]:
    """Extract potential token symbols from text.

    This is a simple extraction based on common patterns.
    More sophisticated NER could be used.

    Args:
        text: Text to extract from

    Returns:
        List of potential token symbols
    """
    if not text:
        return []

    # 常见模式: $TOKEN 或 TOKEN/USDT
    # 匹配全部大写且长度为 2-5 个字符的单词
    pattern = r"\$([A-Z]{2,5})\b"
    tokens = set(re.findall(pattern, text))

    # 也匹配 TOKEN/USDT 模式
    pattern2 = r"\b([A-Z]{2,5})/USDT\b"
    tokens.update(re.findall(pattern2, text))

    return sorted(tokens)
