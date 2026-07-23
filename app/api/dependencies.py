"""FastAPI dependencies that compose application services per request."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from app.database.engine import get_session
from app.database.repositories import (
    SqliteJobExportRepository,
    SqliteJobRepository,
    SqliteJobWorkspaceRepository,
    SqliteProviderRepository,
    SqliteProviderRunRepository,
    SqliteScheduleRepository,
    SqliteSearchRepository,
)
from app.database.repositories.notifications import SqliteNotificationRepository
from app.database.repositories.resumes import SqliteResumeRepository
from app.database.repositories.workspace import SqliteDashboardRepository
from app.exporters.jobs import CsvJobExporter, JsonJobExporter, XlsxJobExporter
from app.exporters.sqlite_backup import SqliteBackupExporter
from app.models.export import ExportFormat
from app.services.dashboard import DashboardService
from app.services.exports import ExportService
from app.services.jobs import JobService
from app.services.manual_searches import ManualSearchService
from app.services.matching import ResumeMatchingService
from app.services.notifications import NotificationService
from app.services.provider_runs import ProviderRunService
from app.services.providers import ProviderService
from app.services.schedules import ScheduleService
from app.services.scoring import JobScoringService
from app.services.searches import SearchService
from app.services.workspace import JobWorkspaceService


def get_job_service(session: Annotated[Session, Depends(get_session)]) -> JobService:
    """Return a job service with a request-scoped SQLite repository."""

    return JobService(SqliteJobRepository(session))


def get_job_workspace_service(
    session: Annotated[Session, Depends(get_session)],
) -> JobWorkspaceService:
    """Return workspace query and workflow-state use cases for one request."""

    return JobWorkspaceService(SqliteJobWorkspaceRepository(session))


def get_job_scoring_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> JobScoringService:
    """Return deterministic job scoring with request-scoped workspace reads."""

    return JobScoringService(
        JobWorkspaceService(SqliteJobWorkspaceRepository(session)),
        request.app.state.settings.scoring,
    )


def get_resume_matching_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> ResumeMatchingService:
    """Return private resume matching with request-scoped persistence and job reads."""

    settings = request.app.state.settings.resume
    return ResumeMatchingService(
        SqliteResumeRepository(session),
        JobWorkspaceService(SqliteJobWorkspaceRepository(session)),
        settings.skill_vocabulary,
        settings.enabled,
        settings.max_upload_characters,
    )


def get_dashboard_service(
    session: Annotated[Session, Depends(get_session)],
) -> DashboardService:
    """Return a dashboard read service backed by one bounded SQL query set."""

    return DashboardService(SqliteDashboardRepository(session))


def get_export_service(request: Request) -> ExportService:
    """Return export use cases with independent streaming sessions and output adapters."""

    settings = request.app.state.settings
    return ExportService(
        repository=SqliteJobExportRepository(request.app.state.engine),
        job_renderers={
            ExportFormat.CSV: CsvJobExporter(),
            ExportFormat.JSON: JsonJobExporter(),
            ExportFormat.XLSX: XlsxJobExporter(),
        },
        backup_renderer=SqliteBackupExporter(settings.database.url),
    )


def get_notification_service(
    session: Annotated[Session, Depends(get_session)],
) -> NotificationService:
    """Return privacy-minimised notification delivery history operations."""

    return NotificationService(SqliteNotificationRepository(session))


def get_provider_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> ProviderService:
    """Return a provider service with a request-scoped SQLite repository."""

    return ProviderService(
        SqliteProviderRepository(session),
        request.app.state.provider_availability,
    )


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


def get_manual_search_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> ManualSearchService:
    """Return a manual-search service using the process-scoped bounded executor."""

    provider_repository = SqliteProviderRepository(session)
    search_repository = SqliteSearchRepository(session)
    run_service = ProviderRunService(
        provider_repository=provider_repository,
        search_repository=search_repository,
        run_repository=SqliteProviderRunRepository(session),
    )
    return ManualSearchService(
        search_service=SearchService(search_repository),
        provider_repository=provider_repository,
        provider_run_service=run_service,
        provider_run_submitter=request.app.state.provider_executor,
    )


def get_schedule_service(
    session: Annotated[Session, Depends(get_session)],
) -> ScheduleService:
    """Return recurring schedule use cases with request-scoped repositories."""

    return ScheduleService(SqliteScheduleRepository(session), SqliteSearchRepository(session))
