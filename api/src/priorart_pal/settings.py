"""App configuration via pydantic-settings.

Reads env vars first, .env file second (local dev only). Secrets are NEVER
hardcoded — production gets them from App Runner's secret env-var injection,
which pulls from Secrets Manager via the instance role.

The `.env` file lives at the **repo root** (`~/Desktop/priorart-pal/.env`),
not under `api/`. Resolving an absolute path here means scripts under
`scripts/` can pick up the same env regardless of cwd.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# api/src/priorart_pal/settings.py -> .../priorart-pal/api/.env  AND  .../priorart-pal/.env
_API_DIR = Path(__file__).resolve().parents[2]  # api/
_REPO_ROOT = _API_DIR.parent  # priorart-pal/

_ENV_FILES = [
    _REPO_ROOT / ".env",  # canonical location for local dev
    _API_DIR / ".env",    # fallback if someone drops one inside api/
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=tuple(str(p) for p in _ENV_FILES),
        env_file_encoding="utf-8",
        env_prefix="PAP_",
        extra="ignore",
    )

    # --- general ---
    env: Literal["dev", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- AI providers ---
    voyage_api_key: str = Field(
        default="", description="Voyage AI key (Secrets Manager in prod)"
    )
    cohere_api_key: str = Field(
        default="", description="Cohere key (Secrets Manager in prod)"
    )
    anthropic_api_key: str = Field(
        default="", description="Anthropic key (Secrets Manager in prod)"
    )

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
