"""Shared fixtures for Job-Hunter tests."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import JsonValue
from sqlmodel import SQLModel

from app.core.config import Settings
from app.database import tables as _tables  # noqa: F401
from app.database.engine import create_database_engine
from app.main import create_app
from app.models.job import JobCandidate
from app.models.search import SearchCriteria
from app.providers.base import BaseProvider
from app.providers.errors import ProviderExecutionError
from app.providers.registry import ProviderRegistry


class FixtureProvider(BaseProvider):
    """Deterministic provider used to test the full manual execution path."""

    code = "fixture"
    display_name = "Fixture Provider"

    def search(
        self,
        criteria: SearchCriteria,
        configuration: Mapping[str, JsonValue],
    ) -> list[JobCandidate]:
        """Return one standard candidate without making a network request."""

        return [
            JobCandidate(
                source=self.code,
                source_job_id="fixture-1",
                source_url="https://jobs.example.test/fixture-1",
                title="Fixture Engineer",
                company="Fixture Company",
                location="Cape Town",
            )
        ]


class FailingFixtureProvider(BaseProvider):
    """Deterministic failing provider used to verify failure isolation."""

    code = "fixture-failing"
    display_name = "Failing Fixture Provider"

    def search(
        self,
        criteria: SearchCriteria,
        configuration: Mapping[str, JsonValue],
    ) -> list[JobCandidate]:
        """Raise a classified expected provider failure."""

        raise ProviderExecutionError()


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


@pytest.fixture
def provider_api_client(settings: Settings) -> TestClient:
    """Return a client whose provider registry contains only deterministic fixtures."""

    engine = create_database_engine(settings.database)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    registry = ProviderRegistry([FixtureProvider, FailingFixtureProvider])
    with TestClient(create_app(settings, registry)) as client:
        yield client
