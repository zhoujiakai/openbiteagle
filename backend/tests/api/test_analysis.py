"""Tests for Analysis API endpoints."""

import pytest


@pytest.mark.usefixtures("mock_settings")
class TestAnalysisAPI:
    """Test analysis API endpoints."""

    def test_create_analysis_with_news_id(
        self, async_client, sample_news
    ):
        """Test creating analysis with existing news_id."""
        response = async_client.post(
            "/api/v1/analysis", json={"news_id": sample_news.id}
        )

        assert response.status_code == 201
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] == "pending"

    def test_create_analysis_with_content(
        self, async_client
    ):
        """Test creating analysis with raw content."""
        response = async_client.post(
            "/api/v1/analysis",
            json={"news_content": "Bitcoin reaches new all-time high today."}
        )

        assert response.status_code == 201
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] == "pending"

    def test_create_analysis_missing_input(
        self, async_client
    ):
        """Test creating analysis without news_id or content."""
        response = async_client.post("/api/v1/analysis", json={})

        assert response.status_code == 400

    def test_create_analysis_invalid_news_id(
        self, async_client
    ):
        """Test creating analysis with non-existent news_id."""
        response = async_client.post(
            "/api/v1/analysis", json={"news_id": 99999}
        )

        assert response.status_code == 400

    def test_batch_create_analysis(
        self, async_client, sample_news
    ):
        """Test batch analysis creation."""
        response = async_client.post(
            "/api/v1/analysis/batch",
            json={"news_ids": [sample_news.id]}
        )

        assert response.status_code == 201
        data = response.json()
        assert "analysis_ids" in data
        assert data["count"] == 1
        assert data["status"] == "pending"

    def test_batch_empty_list(
        self, async_client
    ):
        """Test batch with empty list."""
        response = async_client.post(
            "/api/v1/analysis/batch", json={"news_ids": []}
        )

        assert response.status_code == 422

    def test_get_analysis(
        self, async_client, sample_news
    ):
        """Test getting analysis by ID."""
        # First create an analysis
        create_response = async_client.post(
            "/api/v1/analysis", json={"news_id": sample_news.id}
        )
        assert create_response.status_code == 201
        analysis_id = create_response.json()["analysis_id"]

        # Then get it
        response = async_client.get(f"/api/v1/analysis/{analysis_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == analysis_id
        assert data["news_id"] == sample_news.id
        assert "status" in data

    def test_get_analysis_not_found(
        self, async_client
    ):
        """Test getting non-existent analysis."""
        response = async_client.get("/api/v1/analysis/99999")

        assert response.status_code == 404

    def test_get_overview(
        self, async_client, sample_analysis
    ):
        """Test getting analysis overview."""
        response = async_client.get("/api/v1/analysis/overview")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_value" in data
        assert "top_tokens" in data
        assert "recommendations" in data

    def test_legacy_create_analysis(
        self, async_client, sample_news
    ):
        """Test legacy POST /analysis/news/{news_id} endpoint."""
        response = async_client.post(f"/api/v1/analysis/news/{sample_news.id}")

        assert response.status_code == 200
        data = response.json()
        assert "analysis_id" in data
        assert data["news_id"] == sample_news.id
