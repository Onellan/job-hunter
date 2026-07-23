"""SQLModel repository implementations."""

from app.database.repositories.exports import SqliteJobExportRepository
from app.database.repositories.jobs import SqliteJobRepository
from app.database.repositories.notifications import SqliteNotificationRepository
from app.database.repositories.provider_runs import SqliteProviderRunRepository
from app.database.repositories.providers import SqliteProviderRepository
from app.database.repositories.resumes import SqliteResumeRepository
from app.database.repositories.schedules import SqliteScheduleRepository
from app.database.repositories.searches import SqliteSearchRepository
from app.database.repositories.workspace import (
    SqliteDashboardRepository,
    SqliteJobWorkspaceRepository,
)

__all__ = [
    "SqliteDashboardRepository",
    "SqliteJobExportRepository",
    "SqliteJobRepository",
    "SqliteJobWorkspaceRepository",
    "SqliteNotificationRepository",
    "SqliteProviderRepository",
    "SqliteProviderRunRepository",
    "SqliteResumeRepository",
    "SqliteScheduleRepository",
    "SqliteSearchRepository",
]
