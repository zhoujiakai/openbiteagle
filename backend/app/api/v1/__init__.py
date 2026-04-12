"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import analysis, health, kg, news

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(news.router)
api_router.include_router(analysis.router)
api_router.include_router(kg.router)
