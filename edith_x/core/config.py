"""EDITH-X Configuration — Pydantic Settings"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    edith_env: Literal["development", "staging", "production"] = "development"
    edith_secret_key: str = "dev-secret-key-change-in-production"
    edith_host: str = "0.0.0.0"
    edith_port: int = 8000
    edith_log_level: str = "INFO"

    # LLM Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    nvidia_api_key: str = ""

    # Local Models (LM Studio)
    local_llm_host: str = "http://localhost:1234/v1"
    local_default_model: str = "llama-3.2-3b-instruct"

    # Vector DB
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "edith_x"
    postgres_user: str = "edith"
    postgres_password: str = "edith"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    # Memory
    mem0_api_key: str = ""

    # Semantic Cache
    cache_similarity_threshold: float = 0.92
    cache_ttl_seconds: int = 3600
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Model Routing
    local_models: str = "llama-3.2-3b-instruct"
    cloud_models: str = "nvidia/llama-3.1-70b-instruct,gpt-4o-mini,gpt-4o,claude-3-5-haiku-20241022"

    # Cost Thresholds
    max_cost_per_request_usd: float = 0.10
    escalation_confidence_threshold: float = 0.75

    # Demo
    demo_mode: bool = True
    streamlit_port: int = 8501

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"

    @property
    def local_model_list(self) -> list[str]:
        return [m.strip() for m in self.local_models.split(",") if m.strip()]

    @property
    def cloud_model_list(self) -> list[str]:
        return [m.strip() for m in self.cloud_models.split(",") if m.strip()]

    @property
    def has_local_models(self) -> bool:
        return bool(self.local_model_list)

    @property
    def has_cloud_models(self) -> bool:
        return bool(
            self.openai_api_key or self.anthropic_api_key or
            self.google_api_key or self.groq_api_key or self.nvidia_api_key
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
