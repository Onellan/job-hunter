"""Tests for database infrastructure."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine

from app.core.config import DatabaseSettings
from app.database.engine import create_database_engine, is_database_available


def test_sqlite_engine_is_available(tmp_path: Path) -> None:
    """A file-backed SQLite database is ready when its parent does not exist."""

    database_path = tmp_path / "nested" / "jobs.db"
    engine: Engine = create_database_engine(DatabaseSettings(url=f"sqlite:///{database_path}"))
    try:
        assert is_database_available(engine)
        assert database_path.parent.is_dir()
    finally:
        engine.dispose()
