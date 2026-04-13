"""Analysis API endpoints.

This module provides RESTful API endpoints for news analysis operations.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.news import get_db
from app.core.config import cfg
from app.data.rabbit import get_rabbit
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisCreateResponse,
    AnalysisDetail,
    AnalysisOverview,
    BatchAnalysisCreate,
    BatchAnalysisResponse,
)
from app.services.analysis import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)


async def _queue_analysis(news_id: int, priority: int = 5) -> bool:
    """Queue analysis task to RabbitMQ.

    Args:
        news_id: News ID to analyze
        priority: Task priority (1-10, lower is higher)

    Returns:
        True if queued successfully
    """
    try:
        rabbit = await get_rabbit()
        await rabbit.send(
            queue=cfg.rabbitmq.RABBITMQ_QUEUE,
            message={"news_id": news_id, "priority": priority},
            delivery_mode=2,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to queue analysis for news {news_id}: {e}")
        return False


@router.post("", response_model=AnalysisCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    request: AnalysisCreate,
    db: AsyncSession = Depends(get_db),
) -> AnalysisCreateResponse:
    """Create a new analysis request.

    Accepts either an existing news_id or raw news content.

    **Request:**
    ```json
    {
      "news_id": 123
    }
    ```
    OR
    ```json
    {
      "news_content": "Bitcoin surges to new ATH..."
    }
    ```

    **Response:**
    ```json
    {
      "analysis_id": 456,
      "status": "pending"
    }
    ```

    Args:
        request: Analysis creation request
        db: Database session

    Returns:
        AnalysisCreateResponse with analysis_id and initial status

    Raises:
        HTTPException 400: Invalid request (neither news_id nor content)
        HTTPException 404: News not found (when news_id provided)
    """
    try:
        service = AnalysisService(db)
        response = await service.create_analysis(request)

        # Queue the analysis task
        await _queue_analysis(request.news_id or response.analysis_id)

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create analysis",
        )


@router.post("/batch", response_model=BatchAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_batch_analysis(
    request: BatchAnalysisCreate,
    db: AsyncSession = Depends(get_db),
) -> BatchAnalysisResponse:
    """Create multiple analysis requests.

    **Request:**
    ```json
    {
      "news_ids": [1, 2, 3]
    }
    ```

    **Response:**
    ```json
    {
      "analysis_ids": [101, 102, 103],
      "count": 3,
      "status": "pending"
    }
    ```

    Args:
        request: Batch analysis request
        db: Database session

    Returns:
        BatchAnalysisResponse with list of analysis_ids

    Raises:
        HTTPException 400: Invalid request (empty list or news not found)
    """
    try:
        service = AnalysisService(db)
        response = await service.batch_create_analysis(request)

        # Queue all analysis tasks
        for news_id in request.news_ids:
            await _queue_analysis(news_id)

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating batch analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create batch analysis",
        )


@router.get("/overview", response_model=AnalysisOverview)
async def get_overview(
    db: AsyncSession = Depends(get_db),
) -> AnalysisOverview:
    """Get analysis statistics overview.

    **Response:**
    ```json
    {
      "total": 1000,
      "by_value": {"bullish": 400, "bearish": 200, "neutral": 400},
      "top_tokens": [{"symbol": "BTC", "count": 50}],
      "recommendations": {"buy": 300, "sell": 150, "hold": 550}
    }
    ```

    Args:
        db: Database session

    Returns:
        AnalysisOverview with aggregate statistics
    """
    try:
        from app.services.analysis import get_analysis_overview
        return await get_analysis_overview(db)

    except Exception as e:
        logger.error(f"Error getting overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get overview",
        )


@router.get("/{analysis_id}", response_model=AnalysisDetail)


@router.get("/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
) -> AnalysisDetail:
    """Get analysis result by ID.

    **Response:**
    ```json
    {
      "id": 456,
      "news_id": 123,
      "status": "completed",
      "investment_value": "bullish",
      "confidence": 0.85,
      "tokens": [{"symbol": "BTC", "name": "Bitcoin"}],
      "trend_analysis": "...",
      "recommendation": "buy",
      "steps": [
        {"name": "investment_value", "result": {...}},
        {"name": "extract_tokens", "result": {...}}
      ],
      "created_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:01:00Z"
    }
    ```

    Args:
        analysis_id: Analysis ID
        db: Database session

    Returns:
        AnalysisDetail with full analysis information

    Raises:
        HTTPException 404: Analysis not found
    """
    try:
        service = AnalysisService(db)
        return await service.get_analysis(analysis_id)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analysis",
        )


# Legacy endpoints for backward compatibility
@router.post("/news/{news_id}", response_model=dict, deprecated=True)
async def trigger_analysis_legacy(
    news_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Legacy endpoint: Trigger analysis for a news item.

    **Deprecated:** Use POST /analysis with news_id instead.
    """
    service = AnalysisService(db)
    from app.schemas.analysis import AnalysisCreate
    request = AnalysisCreate(news_id=news_id)
    response = await service.create_analysis(request)
    await _queue_analysis(news_id)
    return {
        "analysis_id": response.analysis_id,
        "news_id": news_id,
        "status": response.status,
    }


@router.get("/news/{news_id}", response_model=dict, deprecated=True)
async def get_analysis_by_news_legacy(
    news_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Legacy endpoint: Get analysis by news ID.

    **Deprecated:** Use GET /analysis/{analysis_id} instead.
    """
    from sqlalchemy import select
    from app.models.analysis import Analysis

    result = await db.execute(
        select(Analysis).where(Analysis.news_id == news_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return {
        "id": analysis.id,
        "news_id": analysis.news_id,
        "status": analysis.status,
        "investment_value": analysis.investment_value,
        "confidence": float(analysis.confidence) if analysis.confidence else None,
        "tokens": analysis.tokens,
        "trend_analysis": analysis.trend_analysis,
        "recommendation": analysis.recommendation,
        "langsmith_trace": analysis.langsmith_trace,
        "error_message": analysis.error_message,
        "retry_count": analysis.retry_count,
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at,
    }


@router.get("/news/{news_id}/status", response_model=dict, deprecated=True)
async def get_analysis_status_legacy(
    news_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Legacy endpoint: Get analysis status by news ID.

    **Deprecated:** Use GET /analysis/{analysis_id} instead.
    """
    from sqlalchemy import select
    from app.models.analysis import Analysis

    result = await db.execute(
        select(Analysis).where(Analysis.news_id == news_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        return {"news_id": news_id, "status": "not_found"}

    return {
        "news_id": news_id,
        "status": analysis.status,
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at,
    }
