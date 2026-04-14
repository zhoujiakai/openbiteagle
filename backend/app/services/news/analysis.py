"""新闻分析服务。"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph import get_graph
from tasks.task2_analyze_flow.graph import get_tracing_config
from app.models.analysis import Analysis
from app.models.news import News


class AnalysisService:
    """新闻分析操作服务。"""

    def __init__(self, db_session: AsyncSession):
        """初始化服务。

        Args:
            db_session: 用于持久化的数据库会话
        """
        self.db = db_session

    async def analyze_news(
        self,
        news_id: int,
        trace_id: Optional[str] = None,
    ) -> dict:
        """对新闻条目运行 LangGraph 分析。

        Args:
            news_id: 要分析的新闻条目 ID
            trace_id: 可选的 LangSmith 追踪 ID，用于关联

        Returns:
            分析结果字典
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
        """获取新闻条目的分析结果。

        Args:
            news_id: 新闻条目 ID

        Returns:
            Analysis 对象或 None
        """
        result = await self.db.execute(
            select(Analysis).where(Analysis.news_id == news_id)
        )
        return result.scalar_one_or_none()

    async def _get_news(self, news_id: int) -> Optional[News]:
        """从数据库获取新闻条目。"""
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
        """将分析结果保存到数据库。"""
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
