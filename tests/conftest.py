"""Shared fixtures for Job-Hunter tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.core.config import Settings
from app.database import tables as _tables  # noqa: F401
from app.database.engine import create_database_engine
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Create isolated settings backed by a temporary SQLite database."""

    database_path = tmp_path / "job-hunter-test.db"
    return Settings.model_validate(
        {
            "app": {"environment": "testing", "version": "test"},
            "database": {"url": f"sqlite:///{database_path}"},
            "logging": {"json_logs": False},
            "security": {"trusted_hosts": ["testserver"]},
        }
    )


@pytest.fixture
def api_client(settings: Settings) -> TestClient:
    """Return a client backed by a temporary database with the current schema."""

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    with TestClient(create_app(settings)) as client:
        yield client
