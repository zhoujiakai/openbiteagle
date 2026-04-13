"""分析 API 端点测试。"""

import pytest


@pytest.mark.usefixtures("mock_settings")
class TestAnalysisAPI:
    """测试分析 API 端点。"""

    def test_create_analysis_with_news_id(
        self, async_client, sample_news
    ):
        """测试使用已有的 news_id 创建分析。"""
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
        """测试使用原始内容创建分析。"""
        response = async_client.post(
            "/api/v1/analysis",
            json={"news_content": "比特币今日创下历史新高。"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] == "pending"

    def test_create_analysis_missing_input(
        self, async_client
    ):
        """测试未提供 news_id 或内容时创建分析。"""
        response = async_client.post("/api/v1/analysis", json={})

        assert response.status_code == 400

    def test_create_analysis_invalid_news_id(
        self, async_client
    ):
        """测试使用不存在的 news_id 创建分析。"""
        response = async_client.post(
            "/api/v1/analysis", json={"news_id": 99999}
        )

        assert response.status_code == 400

    def test_batch_create_analysis(
        self, async_client, sample_news
    ):
        """测试批量创建分析。"""
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
        """测试空列表批量创建。"""
        response = async_client.post(
            "/api/v1/analysis/batch", json={"news_ids": []}
        )

        assert response.status_code == 422

    def test_get_analysis(
        self, async_client, sample_news
    ):
        """测试通过 ID 获取分析。"""
        # 先创建分析
        create_response = async_client.post(
            "/api/v1/analysis", json={"news_id": sample_news.id}
        )
        assert create_response.status_code == 201
        analysis_id = create_response.json()["analysis_id"]

        # 再获取
        response = async_client.get(f"/api/v1/analysis/{analysis_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == analysis_id
        assert data["news_id"] == sample_news.id
        assert "status" in data

    def test_get_analysis_not_found(
        self, async_client
    ):
        """测试获取不存在的分析。"""
        response = async_client.get("/api/v1/analysis/99999")

        assert response.status_code == 404

    def test_get_overview(
        self, async_client, sample_analysis
    ):
        """测试获取分析概览。"""
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
        """测试旧版 POST /analysis/news/{news_id} 端点。"""
        response = async_client.post(f"/api/v1/analysis/news/{sample_news.id}")

        assert response.status_code == 200
        data = response.json()
        assert "analysis_id" in data
        assert data["news_id"] == sample_news.id
