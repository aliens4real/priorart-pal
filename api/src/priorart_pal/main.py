"""FastAPI application factory.

Pattern note: We define `app` at module level so `uvicorn priorart_pal.main:app`
can find it. Configuration happens at import time. Routers are mounted here;
each router lives in its own module under `routers/`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from priorart_pal import __version__
from priorart_pal.logging_config import configure_logging, get_logger
from priorart_pal.routers import health
from priorart_pal.settings import get_settings

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    log.info("api.startup", env=settings.env, version=__version__)
    yield
    log.info("api.shutdown")


app = FastAPI(
    title="PriorArt Pal API",
    version=__version__,
    description="RAG-powered prior-art patent search",
    lifespan=lifespan,
)

app.include_router(health.router)
