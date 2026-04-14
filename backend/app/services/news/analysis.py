"""News analysis service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph import get_graph
from tasks.task2_analyze_flow.graph import get_tracing_config
from app.models.analysis import Analysis
from app.models.news import News


class AnalysisService:
    """Service for news analysis operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the service.

        Args:
            db_session: Database session for persistence
        """
        self.db = db_session

    async def analyze_news(
        self,
        news_id: int,
        trace_id: Optional[str] = None,
    ) -> dict:
        """Run LangGraph analysis on news item.

        Args:
            news_id: News item ID to analyze
            trace_id: Optional LangSmith trace ID for correlation

        Returns:
            Analysis result dict
        """
        # 获取新闻
        news = await self._get_news(news_id)
        if not news:
            raise ValueError(f"News {news_id} not found")

        # 获取已编译的图
        graph = get_graph("news_analysis")

        # 准备输入状态
        input_state = {
            "news_id": news.id,
            "title": news.title,
            "content": news.content or "",
        }

        # 准备带有追踪元数据的配置
        metadata = {
            "news_id": str(news.id),
            "news_title": news.title[:50],
        }
        if trace_id:
            metadata["trace_id"] = trace_id

        config = get_tracing_config(metadata)
        if trace_id:
            config["run_name"] = f"analysis_{news.id}"

        # 运行图
        result = await graph.ainvoke(input_state, config=config)

        # 保存结果
        await self._save_analysis(news_id, result, trace_id)

        return result

    async def get_analysis(self, news_id: int) -> Optional[Analysis]:
        """Get analysis result for a news item.

        Args:
            news_id: News item ID

        Returns:
            Analysis object or None
        """
        result = await self.db.execute(
            select(Analysis).where(Analysis.news_id == news_id)
        )
        return result.scalar_one_or_none()

    async def _get_news(self, news_id: int) -> Optional[News]:
        """Get news item from database."""
        result = await self.db.execute(
            select(News).where(News.id == news_id)
        )
        return result.scalar_one_or_none()

    async def _save_analysis(
        self,
        news_id: int,
        result: dict,
        trace_id: Optional[str] = None,
    ) -> Analysis:
        """Save analysis result to database."""
        from datetime import datetime

        analysis = Analysis(
            news_id=news_id,
            status="completed",
            completed_at=datetime.utcnow(),
            investment_value=result.get("investment_value"),
            confidence=result.get("investment_confidence"),
            tokens=result.get("tokens"),
            trend_analysis=result.get("trend_analysis"),
            recommendation=result.get("recommendation"),
            langsmith_trace=trace_id,
        )

        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)

        return analysis
