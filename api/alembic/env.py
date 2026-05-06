"""Alembic environment.

Migrations run synchronously (one-off operations); we strip the +psycopg
async marker from the URL to use the sync driver. Same database, same
connection params — only the engine type differs.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from priorart_pal.db.models import Base
from priorart_pal.settings import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _sync_url() -> str:
    """Strip the async driver marker so alembic uses sync psycopg."""
    url = get_settings().database_url
    return url.replace("postgresql+psycopg://", "postgresql+psycopg://")


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without connecting to the database."""
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against the live database."""
    config.set_main_option("sqlalchemy.url", _sync_url())
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=False,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
