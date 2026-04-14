"""Biteagle API 主入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import cfg
from app.data.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器。"""
    # 启动
    yield
    # 关闭
    await engine.dispose()


app = FastAPI(
    title=cfg.app.APP_NAME,
    version=cfg.app.APP_VERSION,
    openapi_url=f"/api/v1/openapi.json",
    lifespan=lifespan,
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "healthy", "version": cfg.app.APP_VERSION}


@app.get("/")
async def root():
    """根端点。"""
    return {
        "message": "Welcome to Biteagle API",
        "version": cfg.app.APP_VERSION,
        "docs": "/docs",
    }
