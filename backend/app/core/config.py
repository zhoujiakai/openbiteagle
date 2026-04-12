"""Application configuration."""

from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Biteagle API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # LLM - DeepSeek (primary)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # LLM - OpenAI (fallback)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Embeddings - Jina (free tier)
    JINA_API_KEY: str = ""  # Get free key at https://jina.ai/embeddings
    JINA_EMBEDDING_MODEL: str = "jina-embeddings-v3"

    # LangSmith (optional, for tracing)
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "biteagle"

    # CoinMarketCap (optional, for token market data)
    CMC_API_KEY: str = ""

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://admin:admin@localhost:5672"
    RABBITMQ_QUEUE: str = "biteagle_analysis"
    RABBITMQ_DLQ: str = "biteagle_analysis_dlq"

    # Redis
    REDIS_URL: str = "redis://localhost:6380"

    # Neo4j Knowledge Graph
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "biteagle_password"


settings = Settings()
