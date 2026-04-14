"""分析服务层。

该模块处理新闻分析操作的业务逻辑。
"""

import logging
from collections import Counter
from typing import Optional

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.news import News
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisCreateResponse,
    AnalysisDetail,
    BatchAnalysisCreate,
    BatchAnalysisResponse,
    AnalysisOverview,
    TokenCount,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    """管理新闻分析操作的服务。"""

    def __init__(self, db: AsyncSession):
        """使用数据库会话初始化服务。

        Args:
            db: 异步数据库会话
        """
        self.db = db

    async def create_analysis(
        self,
        request: AnalysisCreate,
    ) -> AnalysisCreateResponse:
        """创建一个新闻分析请求

        Args:
            request: Analysis creation request with news_id or news_content

        Returns:
            AnalysisCreateResponse with analysis_id and status

        Raises:
            ValueError: If neither news_id nor news_content provided
            HTTPException: If news not found (when news_id provided)
        """
        # 确定 news_id
        news_id: Optional[int] = None

        if request.news_id is not None:
            # 验证新闻是否存在
            result = await self.db.execute(
                select(News).where(News.id == request.news_id)
            )
            news = result.scalar_one_or_none()
            if not news:
                raise ValueError(f"News with id {request.news_id} not found")
            news_id = request.news_id
        elif request.news_content:
            # 从内容创建新闻记录
            news = News(
                title=request.news_content[:200] + "..."
                if len(request.news_content) > 200
                else request.news_content,
                content=request.news_content,
            )
            self.db.add(news)
            await self.db.flush()
            news_id = news.id
        else:
            raise ValueError("Either news_id or news_content must be provided")

        # 检查是否已有分析
        existing = await self.db.execute(
            select(Analysis).where(Analysis.news_id == news_id)
        )
        existing_analysis = existing.scalar_one_or_none()

        if existing_analysis:
            # 返回已有分析
            logger.info(f"Found existing analysis {existing_analysis.id} for news {news_id}")
            return AnalysisCreateResponse(
                analysis_id=existing_analysis.id, news_id=news_id, status=existing_analysis.status
            )

        # 创建新分析
        analysis = Analysis(
            news_id=news_id,
            status="pending",
            steps=None,
        )
        self.db.add(analysis)
        await self.db.flush()

        logger.info(f"Created analysis {analysis.id} for news {news_id}")

        return AnalysisCreateResponse(analysis_id=analysis.id, news_id=news_id, status="pending")

    async def batch_create_analysis(
        self,
        request: BatchAnalysisCreate,
    ) -> BatchAnalysisResponse:
        """创建多个分析请求。

        Args:
            request: 包含 news_ids 列表的批量分析请求

        Returns:
            包含 analysis_ids 列表的 BatchAnalysisResponse

        Raises:
            ValueError: 如果任何 news_id 未找到
        """
        # 验证所有新闻是否存在
        result = await self.db.execute(
            select(News).where(News.id.in_(request.news_ids))
        )
        found_news = {news.id for news in result.scalars().all()}

        missing = set(request.news_ids) - found_news
        if missing:
            raise ValueError(f"News not found for ids: {missing}")

        analysis_ids: list[int] = []

        for news_id in request.news_ids:
            # 检查是否已有分析
            existing = await self.db.execute(
                select(Analysis).where(Analysis.news_id == news_id)
            )
            existing_analysis = existing.scalar_one_or_none()

            if existing_analysis:
                analysis_ids.append(existing_analysis.id)
            else:
                analysis = Analysis(news_id=news_id, status="pending")
                self.db.add(analysis)
                await self.db.flush()
                analysis_ids.append(analysis.id)

        logger.info(f"Created {len(analysis_ids)} analyses for batch request")

        return BatchAnalysisResponse(
            analysis_ids=analysis_ids, count=len(analysis_ids), status="pending"
        )

    async def get_analysis(self, analysis_id: int) -> AnalysisDetail:
        """根据 ID 获取分析详情。

        Args:
            analysis_id: 分析 ID

        Returns:
            包含所有信息（包括步骤）的 AnalysisDetail

        Raises:
            ValueError: 如果分析未找到
        """
        result = await self.db.execute(
            select(Analysis).where(Analysis.id == analysis_id)
        )
        analysis = result.scalar_one_or_none()

        if not analysis:
            raise ValueError(f"Analysis with id {analysis_id} not found")

        # 从 JSONB 解析步骤
        steps = None
        if analysis.steps:
            from app.schemas.analysis import StepResult
            steps = [StepResult(**s) for s in analysis.steps.get("steps", [])]

        return AnalysisDetail(
            id=analysis.id,
            news_id=analysis.news_id,
            status=analysis.status,
            investment_value=analysis.investment_value,
            confidence=float(analysis.confidence) if analysis.confidence else None,
            tokens=analysis.tokens,
            trend_analysis=analysis.trend_analysis,
            recommendation=analysis.recommendation,
            steps=steps,
            langsmith_trace=analysis.langsmith_trace,
            error_message=analysis.error_message,
            retry_count=analysis.retry_count,
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
        )

    async def get_overview(self) -> AnalysisOverview:
        """获取分析统计概览。

        Returns:
            包含汇总统计的 AnalysisOverview
        """
        # 总数统计
        total_result = await self.db.execute(
            select(sql_func.count()).select_from(Analysis)
        )
        total = total_result.scalar() or 0

        # 按投资价值分组
        value_result = await self.db.execute(
            select(Analysis.investment_value, sql_func.count(Analysis.id))
            .where(Analysis.investment_value.isnot(None))
            .group_by(Analysis.investment_value)
        )
        by_value = {value: count for value, count in value_result.all()}

        # 按推荐分组
        rec_result = await self.db.execute(
            select(Analysis.recommendation, sql_func.count(Analysis.id))
            .where(Analysis.recommendation.isnot(None))
            .group_by(Analysis.recommendation)
        )
        recommendations = {rec: count for rec, count in rec_result.all()}

        # 热门代币（从 tokens JSONB 中提取）
        token_counts: Counter = Counter()
        token_result = await self.db.execute(
            select(Analysis.tokens).where(
                Analysis.tokens.isnot(None),
                Analysis.tokens != {},  # type: ignore
            )
        )
        for tokens, in token_result.all():
            if isinstance(tokens, dict) and "tokens" in tokens:
                for token in tokens["tokens"]:
                    if isinstance(token, dict) and "symbol" in token:
                        token_counts[token["symbol"]] += 1

        top_tokens = [
            TokenCount(symbol=symbol, count=count)
            for symbol, count in token_counts.most_common(10)
        ]

        return AnalysisOverview(
            total=total,
            by_value=by_value,
            top_tokens=top_tokens,
            recommendations=recommendations,
        )


async def create_analysis(
    db: AsyncSession,
    request: AnalysisCreate,
) -> AnalysisCreateResponse:
    """创建分析的便捷函数。

    Args:
        db: 数据库会话
        request: 分析创建请求

    Returns:
        AnalysisCreateResponse
    """
    service = AnalysisService(db)
    return await service.create_analysis(request)


async def get_analysis_overview(
    db: AsyncSession,
) -> AnalysisOverview:
    """获取分析概览的便捷函数。

    Args:
        db: 数据库会话

    Returns:
        AnalysisOverview
    """
    service = AnalysisService(db)
    return await service.get_overview()
