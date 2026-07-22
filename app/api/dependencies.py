"""FastAPI dependencies that compose application services per request."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.database.engine import get_session
from app.database.repositories import (
    SqliteJobRepository,
    SqliteProviderRepository,
    SqliteProviderRunRepository,
    SqliteSearchRepository,
)
from app.services.jobs import JobService
from app.services.provider_runs import ProviderRunService
from app.services.providers import ProviderService
from app.services.searches import SearchService


def get_job_service(session: Annotated[Session, Depends(get_session)]) -> JobService:
    """Return a job service with a request-scoped SQLite repository."""

    return JobService(SqliteJobRepository(session))


def get_provider_service(session: Annotated[Session, Depends(get_session)]) -> ProviderService:
    """Return a provider service with a request-scoped SQLite repository."""

    return ProviderService(SqliteProviderRepository(session))


def get_search_service(session: Annotated[Session, Depends(get_session)]) -> SearchService:
    """Return a saved-search service with a request-scoped SQLite repository."""

    return SearchService(SqliteSearchRepository(session))


def get_provider_run_service(
    session: Annotated[Session, Depends(get_session)],
) -> ProviderRunService:
    """Return a run service with repositories required for reference validation."""

    return ProviderRunService(
        provider_repository=SqliteProviderRepository(session),
        search_repository=SqliteSearchRepository(session),
        run_repository=SqliteProviderRunRepository(session),
    )
