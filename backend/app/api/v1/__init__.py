"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import health, kg, news
from tasks.task3_mq_driven.analysis import router as analysis_router

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(news.router)
api_router.include_router(analysis_router)
api_router.include_router(kg.router)
