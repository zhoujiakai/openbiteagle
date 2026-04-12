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

    # Remove script and style elements
    cleaned = re.sub(r"<(script|style).*?>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)

    # Use bleach to clean HTML (remove all tags)
    cleaned = bleach.clean(cleaned, tags=[], strip=True)

    # Decode HTML entities
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

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove control characters
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

    # Remove common prefixes
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

    # Check for spam/invalid content patterns
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

    # Common pattern: $TOKEN or TOKEN/USDT
    # Match words that are all caps and 2-5 characters
    pattern = r"\$([A-Z]{2,5})\b"
    tokens = set(re.findall(pattern, text))

    # Also match TOKEN/USDT pattern
    pattern2 = r"\b([A-Z]{2,5})/USDT\b"
    tokens.update(re.findall(pattern2, text))

    return sorted(tokens)
