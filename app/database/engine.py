"""SQLModel engine and session lifecycle helpers."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy import event
from sqlalchemy.engine import Engine, make_url
from sqlmodel import Session, create_engine

from app.core.config import DatabaseSettings


def create_database_engine(settings: DatabaseSettings) -> Engine:
    """Create an engine without opening a connection during application startup.

    Args:
        settings: Validated database connection settings.

    Returns:
        A configured SQLAlchemy engine suitable for SQLModel sessions.
    """

    url = make_url(settings.url)
    connect_args: dict[str, bool] = {}
    if url.drivername.startswith("sqlite"):
        _ensure_sqlite_directory(url.database)
        connect_args["check_same_thread"] = False

    engine = create_engine(settings.url, connect_args=connect_args, echo=settings.echo)
    if url.drivername.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _ensure_sqlite_directory(database_path: str | None) -> None:
    """Create the parent directory for a file-backed SQLite database."""

    if database_path is None or database_path == ":memory:":
        return
    Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
    """Enable SQLite foreign-key enforcement for every new connection."""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_session(request: Request) -> Generator[Session, None, None]:
    """Yield a request-scoped SQLModel session from application state."""

    engine: Engine = request.app.state.engine
    with Session(engine) as session:
        yield session


def is_database_available(engine: Engine) -> bool:
    """Return whether the database accepts a lightweight connectivity query."""

    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except Exception:  # The health endpoint must report failures, not raise them.
        return False
    return True
