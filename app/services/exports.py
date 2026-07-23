"""Application service that coordinates low-memory exports and audit events."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from app.models.common import PaginatedResult, utc_now
from app.models.export import ExportDownload, ExportEventRecord, ExportFormat, JobExportRequest
from app.models.export_errors import ExportUnavailableError
from app.services.ports import DatabaseBackupRenderer, JobExportRenderer, JobExportRepository

logger = logging.getLogger(__name__)


class ExportService:
    """Coordinate export reads, renderer adapters, and privacy-safe audit records."""

    def __init__(
        self,
        repository: JobExportRepository,
        job_renderers: Mapping[ExportFormat, JobExportRenderer],
        backup_renderer: DatabaseBackupRenderer,
    ) -> None:
        """Create the service with persistence and output adapters at its boundary."""

        self._repository = repository
        self._job_renderers = job_renderers
        self._backup_renderer = backup_renderer

    def export_jobs(self, request: JobExportRequest) -> ExportDownload:
        """Record and render selected jobs or a filtered stream without large lists."""

        renderer = self._job_renderers.get(request.format)
        if renderer is None:
            raise ExportUnavailableError(
                "Use the dedicated SQLite backup export for database downloads."
            )
        job_count = self._repository.count_jobs(request, request.job_ids)
        event = self._repository.create_event(request.format, "jobs", job_count, utc_now())
        logger.info(
            "job_export_requested",
            extra={
                "export_event_id": str(event.id),
                "format": request.format,
                "job_count": job_count,
            },
        )
        return renderer.render(self._repository.iter_jobs(request, request.job_ids))

    def export_sqlite_backup(self) -> ExportDownload:
        """Record and create a consistent file-backed SQLite backup download."""

        event = self._repository.create_event(ExportFormat.SQLITE, "database", None, utc_now())
        logger.info("database_backup_requested", extra={"export_event_id": str(event.id)})
        return self._backup_renderer.render()

    def list_events(self, offset: int, limit: int) -> PaginatedResult[ExportEventRecord]:
        """Return a bounded audit history for operators and API clients."""

        return self._repository.list_events(offset, limit)
