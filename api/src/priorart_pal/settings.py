"""App configuration via pydantic-settings.

Reads env vars first, .env file second (local dev only). Secrets are NEVER
hardcoded — production gets them from App Runner's secret env-var injection,
which pulls from Secrets Manager via the instance role.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PAP_",
        extra="ignore",
    )

    # --- general ---
    env: Literal["dev", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- AI providers ---
    voyage_api_key: str = Field(default="", description="Voyage AI key (Secrets Manager in prod)")
    cohere_api_key: str = Field(default="", description="Cohere key (Secrets Manager in prod)")
    anthropic_api_key: str = Field(default="", description="Anthropic key (Secrets Manager in prod)")

    embedding_model: str = "voyage-3-large"
    rerank_model: str = "rerank-v3.5"
    generation_model: str = "claude-sonnet-4-6"

    # --- database ---
    database_url: str = Field(
        default="postgresql+psycopg://localhost:5432/priorart_pal",
        description="SQLAlchemy URL — overridden by App Runner in prod",
    )

    # --- Bedrock swap flag (left available per architecture spec) ---
    use_bedrock: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
