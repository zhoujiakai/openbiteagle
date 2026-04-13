"""图测试的固件。"""

import pytest


@pytest.fixture
def mock_openai_api_key(monkeypatch):
    """设置模拟 OpenAI API Key 用于测试。"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-testing")
    return "test-key-for-testing"
