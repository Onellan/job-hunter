"""Repository contracts consumed by application services."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.models.common import PaginatedResult
from app.models.dashboard import DashboardSnapshot
from app.models.export import ExportDownload, ExportEventRecord, ExportFormat, JobExportScope
from app.models.job import JobCandidate, JobRecord
from app.models.matching import ResumeProfile
from app.models.provider import ProviderCreate, ProviderRecord, ProviderUpdate
from app.models.provider_run import ProviderRunCreate, ProviderRunRecord, ProviderRunUpdate
from app.models.schedule import (
    ScheduleCreate,
    ScheduleRecord,
    ScheduleRunRecord,
    ScheduleRunStatus,
    ScheduleUpdate,
)
from app.models.search import SearchCreate, SearchRecord, SearchUpdate
from app.models.workspace import (
    JobWorkflowRecord,
    JobWorkflowUpdate,
    JobWorkspaceItem,
    JobWorkspaceQuery,
)


class JobRepository(Protocol):
    """Persistence operations required for provider-neutral jobs."""

    def get(self, job_id: UUID) -> JobRecord | None:
        """Return a job by ID when it exists."""

    def find_by_source_identity(self, source: str, source_job_id: str) -> JobRecord | None:
        """Return a job by the provider's stable identifier."""

    def find_by_source_url(self, source_url: str) -> JobRecord | None:
        """Return a job by its canonical source URL."""

    def find_by_fingerprint(self, fingerprint: str) -> JobRecord | None:
        """Return a job by its deterministic fallback identity."""

    def create(self, candidate: JobCandidate, fingerprint: str, now: datetime) -> JobRecord:
        """Persist a new job candidate."""

    def update(
        self,
        job_id: UUID,
        candidate: JobCandidate,
        fingerprint: str,
        now: datetime,
    ) -> JobRecord:
        """Persist the latest version of a known job candidate."""

    def list(self, offset: int, limit: int, source: str | None) -> PaginatedResult[JobRecord]:
        """Return jobs ordered by the latest observation time."""

    def delete(self, job_id: UUID) -> bool:
        """Delete a job and report whether it existed."""


class JobWorkspaceRepository(Protocol):
    """Persistence reads and user-state writes specific to the job workspace."""

    def get(self, job_id: UUID) -> JobWorkspaceItem | None:
        """Return one job joined to its optional workflow state."""

    def list(self, query: JobWorkspaceQuery) -> PaginatedResult[JobWorkspaceItem]:
        """Return a filtered and sorted bounded workspace page."""

    def update_workflow(
        self,
        job_id: UUID,
        changes: JobWorkflowUpdate,
        now: datetime,
    ) -> JobWorkflowRecord | None:
        """Create or update workflow state for an existing job."""

    def bulk_update_workflow(
        self,
        job_ids: Sequence[UUID],
        changes: JobWorkflowUpdate,
        now: datetime,
    ) -> int:
        """Apply one workflow update to known jobs and return their count."""


class DashboardRepository(Protocol):
    """Bounded dashboard read model independent of the HTTP presentation."""

    def get_snapshot(self, today_start: datetime) -> DashboardSnapshot:
        """Return current metrics, recent searches, and latest jobs."""


class JobExportRepository(Protocol):
    """Stream-safe job export reads that do not materialise a complete result set."""

    def count_jobs(self, scope: JobExportScope, job_ids: Sequence[UUID]) -> int:
        """Return the number of matching jobs for audit metadata."""

    def iter_jobs(
        self,
        scope: JobExportScope,
        job_ids: Sequence[UUID],
    ) -> Iterator[JobWorkspaceItem]:
        """Yield matching workspace jobs in fixed-size database batches."""

    def create_event(
        self,
        export_format: ExportFormat,
        resource: str,
        selected_job_count: int | None,
        now: datetime,
    ) -> ExportEventRecord:
        """Persist one audit event before a download response begins."""

    def list_events(self, offset: int, limit: int) -> PaginatedResult[ExportEventRecord]:
        """Return a bounded newest-first page of export audit events."""


class JobExportRenderer(Protocol):
    """Render a streaming or temporary-file job download from an iterator."""

    def render(self, jobs: Iterable[JobWorkspaceItem]) -> ExportDownload:
        """Create a download while preserving bounded source iteration."""


class DatabaseBackupRenderer(Protocol):
    """Create a downloadable backup of the configured durable database."""

    def render(self) -> ExportDownload:
        """Create a consistent backup download without an in-memory database copy."""


class ProviderRepository(Protocol):
    """Persistence operations required for provider registrations."""

    def get(self, provider_id: UUID) -> ProviderRecord | None:
        """Return a provider by ID when it exists."""

    def create(self, provider: ProviderCreate, now: datetime) -> ProviderRecord:
        """Persist a provider registration."""

    def create_missing(self, providers: Sequence[ProviderCreate], now: datetime) -> None:
        """Create only missing provider codes without changing existing rows."""

    def update(
        self,
        provider_id: UUID,
        changes: ProviderUpdate,
        now: datetime,
    ) -> ProviderRecord | None:
        """Apply mutable provider settings."""

    def list(self, offset: int, limit: int) -> PaginatedResult[ProviderRecord]:
        """Return registered providers ordered by display name."""

    def list_enabled(self, codes: set[str] | None) -> Sequence[ProviderRecord]:
        """Return enabled providers, optionally limited to configured codes."""

    def delete(self, provider_id: UUID) -> bool:
        """Delete a provider and report whether it existed."""


class SearchRepository(Protocol):
    """Persistence operations required for saved searches."""

    def get(self, search_id: UUID) -> SearchRecord | None:
        """Return a saved search by ID when it exists."""

    def create(self, search: SearchCreate, now: datetime) -> SearchRecord:
        """Persist a saved search."""

    def update(self, search_id: UUID, changes: SearchUpdate, now: datetime) -> SearchRecord | None:
        """Apply mutable saved-search settings."""

    def list(self, offset: int, limit: int) -> PaginatedResult[SearchRecord]:
        """Return saved searches ordered by name."""

    def delete(self, search_id: UUID) -> bool:
        """Delete a saved search and report whether it existed."""


class ProviderRunRepository(Protocol):
    """Persistence operations required for provider execution state."""

    def get(self, run_id: UUID) -> ProviderRunRecord | None:
        """Return a provider run by ID when it exists."""

    def create(self, provider_run: ProviderRunCreate, now: datetime) -> ProviderRunRecord:
        """Persist a pending provider run."""

    def update(
        self,
        run_id: UUID,
        changes: ProviderRunUpdate,
        started_at: datetime | None,
        finished_at: datetime | None,
        now: datetime,
    ) -> ProviderRunRecord | None:
        """Apply a validated provider-run state update."""

    def list(
        self,
        offset: int,
        limit: int,
        provider_id: UUID | None,
        search_id: UUID | None,
    ) -> PaginatedResult[ProviderRunRecord]:
        """Return provider runs ordered by newest creation time."""

    def delete(self, run_id: UUID) -> bool:
        """Delete a provider run and report whether it existed."""


class ProviderRunSubmitter(Protocol):
    """A bounded infrastructure adapter that accepts durable provider run IDs."""

    def submit(self, run_id: UUID) -> bool:
        """Schedule a run without blocking an HTTP request."""


class ScheduleRepository(Protocol):
    """Persistence operations required for schedule definitions and their history."""

    def get(self, schedule_id: UUID) -> ScheduleRecord | None:
        """Return a schedule by ID when it exists."""

    def create(self, schedule: ScheduleCreate, now: datetime) -> ScheduleRecord:
        """Persist a schedule definition."""

    def update(
        self, schedule_id: UUID, changes: ScheduleUpdate, now: datetime
    ) -> ScheduleRecord | None:
        """Persist mutable schedule fields."""

    def list(self, offset: int, limit: int) -> PaginatedResult[ScheduleRecord]:
        """Return schedules in a bounded page."""

    def delete(self, schedule_id: UUID) -> bool:
        """Delete a schedule definition."""

    def create_run(
        self, schedule_id: UUID, search_id: UUID, attempt: int, manual: bool, now: datetime
    ) -> ScheduleRunRecord:
        """Create one dispatch-history row."""

    def finish_run(
        self,
        run_id: UUID,
        status: ScheduleRunStatus,
        provider_run_count: int,
        failed_provider_count: int,
        error_summary: str | None,
        now: datetime,
    ) -> ScheduleRunRecord | None:
        """Persist a dispatch outcome."""

    def mark_dispatched(self, schedule_id: UUID, now: datetime) -> None:
        """Persist the latest dispatch timestamp."""

    def list_runs(
        self, schedule_id: UUID, offset: int, limit: int
    ) -> PaginatedResult[ScheduleRunRecord]:
        """Return a bounded schedule dispatch history."""


class ResumeRepository(Protocol):
    """Persistence needed for the single active local resume skill profile."""

    def get(self) -> ResumeProfile | None:
        """Return the active resume-derived profile when present."""

    def replace(self, skills: list[str], now: datetime) -> ResumeProfile:
        """Replace the active profile's derived skills and consent metadata."""

    def delete(self) -> bool:
        """Delete the active profile and its consent metadata."""
