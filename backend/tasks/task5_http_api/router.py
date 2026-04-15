"""分析 API 接口。

本模块提供新闻分析相关的 RESTful API 接口。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.db import get_db
from app.core.config import cfg
from app.data.logger import create_logger
from app.data.rabbit import get_rabbit
from app.schemas.analysis import (
    AnalysisCreate,
    AnalysisCreateResponse,
    AnalysisDetail,
    AnalysisOverview,
    BatchAnalysisCreate,
    BatchAnalysisResponse,
)
from tasks.task5_http_api.service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = create_logger("分析API路由")


async def _queue_analysis(news_id: int, priority: int = 5) -> bool:
    """分析任务入队

    Args:
        news_id: 需要分析的新闻ID
        priority: 任务优先级 (1-10, 值越小优先级越高)

    Returns:
        入队成功返回True
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
        logger.error(f"新闻 {news_id} 分析任务入队失败: {e}")
        return False


@router.post("", response_model=AnalysisCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    request: AnalysisCreate,
    db: AsyncSession = Depends(get_db),
) -> AnalysisCreateResponse:
    """创建一个新闻分析请求

    接受已有的 news_id 或原始新闻内容。

    **请求示例:**
    ```json
    {
      "news_id": 123
    }
    ```
    或
    ```json
    {
      "news_content": "Bitcoin surges to new ATH..."
    }
    ```

    **响应示例:**
    ```json
    {
      "analysis_id": 456,
      "status": "pending"
    }
    ```

    Args:
        request: 分析创建请求
        db: 数据库会话

    Returns:
        返回包含 analysis_id 和初始状态的 AnalysisCreateResponse

    Raises:
        HTTPException 400: 无效请求（未提供 news_id 或内容）
        HTTPException 404: 新闻未找到（提供 news_id 时）
    """
    try:
        service = AnalysisService(db)
        response = await service.create_analysis(request)

        # 将分析任务加入队列
        await _queue_analysis(response.news_id)

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"创建分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建分析失败",
        )


@router.post("/batch", response_model=BatchAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_batch_analysis(
    request: BatchAnalysisCreate,
    db: AsyncSession = Depends(get_db),
) -> BatchAnalysisResponse:
    """批量创建分析请求。

    **请求示例:**
    ```json
    {
      "news_ids": [1, 2, 3]
    }
    ```

    **响应示例:**
    ```json
    {
      "analysis_ids": [101, 102, 103],
      "count": 3,
      "status": "pending"
    }
    ```

    Args:
        request: 批量分析请求
        db: 数据库会话

    Returns:
        返回包含 analysis_ids 列表的 BatchAnalysisResponse

    Raises:
        HTTPException 400: 无效请求（列表为空或新闻未找到）
    """
    try:
        service = AnalysisService(db)
        response = await service.batch_create_analysis(request)

        # 将所有分析任务加入队列
        for news_id in request.news_ids:
            await _queue_analysis(news_id)

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"批量创建分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量创建分析失败",
        )


@router.get("/overview", response_model=AnalysisOverview)
async def get_overview(
    db: AsyncSession = Depends(get_db),
) -> AnalysisOverview:
    """获取分析统计概览。

    **响应示例:**
    ```json
    {
      "total": 1000,
      "by_value": {"bullish": 400, "bearish": 200, "neutral": 400},
      "top_tokens": [{"symbol": "BTC", "count": 50}],
      "recommendations": {"buy": 300, "sell": 150, "hold": 550}
    }
    ```

    Args:
        db: 数据库会话

    Returns:
        返回包含聚合统计信息的 AnalysisOverview
    """
    try:
        from tasks.task5_http_api.service import get_analysis_overview
        return await get_analysis_overview(db)

    except Exception as e:
        logger.error(f"获取概览失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取概览失败",
        )


@router.get("/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
) -> AnalysisDetail:
    """根据 ID 获取分析结果。

    **响应示例:**
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
        analysis_id: 分析记录 ID
        db: 数据库会话

    Returns:
        返回包含完整分析信息的 AnalysisDetail

    Raises:
        HTTPException 404: 分析记录未找到
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
        logger.error(f"获取分析 {analysis_id} 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取分析失败",
        )
