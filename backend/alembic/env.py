"""Alembic environment for Tradeo.

Resolves the database URL from application settings (TRADEO_DATABASE_URL) so
migrations always target the same database as the app. ``target_metadata`` is
the app's declarative Base so ``alembic revision --autogenerate`` works for
future revisions.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from tradeo.core.config import get_settings
from tradeo.db import models  # noqa: F401  (register all models on Base.metadata)
from tradeo.db.session import Base

config = context.config

target_metadata = Base.metadata


def _database_url() -> str:
    override = config.get_main_option("sqlalchemy.url")
    if override:
        return override
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), pool_pre_ping=True, future=True)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
