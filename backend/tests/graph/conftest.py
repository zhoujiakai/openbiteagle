"""Fixtures for graph tests."""

import pytest


@pytest.fixture
def mock_openai_api_key(monkeypatch):
    """Set mock OpenAI API key for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-for-testing")
    return "test-key-for-testing"
