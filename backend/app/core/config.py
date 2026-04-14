"""Application configuration loaded from config.yaml."""

import os
from pathlib import Path
from typing import List

import yaml


class Config:
    """YAML-based application configuration."""

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    def __init__(self) -> None:
        self.load_config()

    def load_config(self) -> None:
        config_file_path = self.BASE_DIR / "config.yaml"
        if not config_file_path.exists():
            return
        with open(config_file_path, encoding="utf-8") as file:
            raw = yaml.safe_load(file) or {}
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            section_cls = getattr(self.__class__, k, None)
            if section_cls is None or not isinstance(section_cls, type):
                continue
            for k2, v2 in v.items():
                setattr(section_cls, k2, v2)

        # 将 LangSmith 配置同步到环境变量，使 LangChain 自动追踪生效
        self._sync_langsmith_env()

    def _sync_langsmith_env(self) -> None:
        """将 LangSmith 配置写入 os.environ，LangChain 运行时依赖这些环境变量。"""
        for attr in ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT"):
            val = getattr(self.langsmith, attr, None)
            if val:
                os.environ[attr] = str(val)

    # ── Application ──────────────────────────────────────
    class app:
        APP_NAME: str = "Biteagle API"
        APP_VERSION: str = "0.1.0"
        DEBUG: bool = False
        HOST: str = "0.0.0.0"
        PORT: int = 8000

    # ── Database ─────────────────────────────────────────
    class database:
        DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/biteagle"
        DATABASE_SCHEMA: str = "biteagle"

    # ── Security ─────────────────────────────────────────
    class security:
        SECRET_KEY: str = "your-secret-key-here-change-in-production"
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── CORS ─────────────────────────────────────────────
    class cors:
        CORS_ORIGINS: List[str] = []

    # ── LLM - DeepSeek (primary) ────────────────────────
    class deepseek:
        DEEPSEEK_API_KEY: str = ""
        DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
        DEEPSEEK_MODEL: str = "deepseek-chat"

    # ── LLM - OpenAI (fallback) ─────────────────────────
    class openai:
        OPENAI_API_KEY: str = ""
        OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Embeddings - Jina ────────────────────────────────
    class jina:
        JINA_API_KEY: str = ""
        JINA_EMBEDDING_MODEL: str = "jina-embeddings-v3"
        JINA_API_URL: str = "https://api.jina.ai/v1/embeddings"
        JINA_EMBEDDING_DIM: int = 1024
        JINA_BATCH_SIZE: int = 8
        JINA_TIMEOUT: float = 30.0
        CHUNK_SIZE: int = 500
        CHUNK_OVERLAP: int = 100

    # ── LangSmith (optional) ────────────────────────────
    class langsmith:
        LANGCHAIN_TRACING_V2: str = "false"
        LANGCHAIN_API_KEY: str = ""
        LANGCHAIN_PROJECT: str = "biteagle"

    # ── CoinMarketCap ───────────────────────────────────
    class cmc:
        CMC_API_KEY: str = ""

    # ── RabbitMQ ─────────────────────────────────────────
    class rabbitmq:
        RABBITMQ_URL: str = "amqp://admin:admin@localhost:5672"
        RABBITMQ_QUEUE: str = "biteagle_analysis"
        RABBITMQ_DLQ: str = "biteagle_analysis_dlq"

    # ── Redis ────────────────────────────────────────────
    class redis:
        REDIS_URL: str = "redis://localhost:6380"

    # ── Worker ───────────────────────────────────────────
    class worker:
        MAX_RETRIES: int = 3
        CONCURRENCY: int = 5
        RETRY_BASE_DELAY: int = 5
        TASK_TTL: int = 3600

    # ── Aliyun OSS ───────────────────────────────────────
    class oss:
        OSS_ACCESS_KEY_ID: str = ""
        OSS_ACCESS_KEY_SECRET: str = ""
        OSS_ENDPOINT: str = "oss-cn-hangzhou.aliyuncs.com"
        OSS_BUCKET_NAME: str = ""

    # ── Neo4j Knowledge Graph ───────────────────────────
    class neo4j:
        NEO4J_URI: str = "bolt://localhost:7687"
        NEO4J_USER: str = "neo4j"
        NEO4J_PASSWORD: str = "biteagle_password"
        NEO4J_MAX_CONNECTION_LIFETIME: int = 3600
        NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50
        NEO4J_CONNECTION_ACQUISITION_TIMEOUT: int = 60

    # ── RootData REST API ───────────────────────────────
    class rootdata:
        ROOTDATA_API_KEY: str = ""
        ROOTDATA_BASE_URL: str = "https://api.rootdata.com/open"
        ROOTDATA_LANGUAGE: str = "en"
        ROOTDATA_TIMEOUT: float = 15.0


cfg = Config()
