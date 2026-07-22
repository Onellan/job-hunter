"""Alembic environment configured from Job-Hunter's validated settings."""

from __future__ import annotations

from alembic import context
from sqlmodel import SQLModel

from app.core.config import DatabaseSettings, get_settings
from app.database import tables as _tables  # noqa: F401
from app.database.engine import create_database_engine

config = context.config

target_metadata = SQLModel.metadata


def _database_settings() -> DatabaseSettings:
    """Return the migration URL override or the normal validated database URL."""

    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return DatabaseSettings(url=configured_url)
    return get_settings().database


def run_migrations_offline() -> None:
    """Run migrations without opening a database connection."""

    context.configure(
        url=_database_settings().url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a short-lived configured database connection."""

    connectable = create_database_engine(_database_settings())
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
