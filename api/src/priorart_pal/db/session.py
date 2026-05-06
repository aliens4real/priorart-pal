"""Async SQLAlchemy session + engine for PriorArt Pal.

Pattern note: FastAPI is async, so the database session is async too.
SQLAlchemy 2.0 + psycopg 3 supports async natively. The
`postgresql+psycopg://...` URL scheme dispatches to psycopg's async
driver when used through `create_async_engine`.

Usage in a route:

    from fastapi import Depends
    from priorart_pal.db.session import get_session

    @router.get("/something")
    async def handler(session = Depends(get_session)):
        result = await session.execute(...)
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from priorart_pal.settings import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazily create the engine. One per process."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(), expire_on_commit=False
        )
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency for an async session per request."""
    async with get_sessionmaker()() as session:
        yield session


async def close_engine() -> None:
    """Dispose the engine. Called from FastAPI lifespan shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
