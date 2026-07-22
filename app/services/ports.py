"""Repository contracts consumed by application services."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.models.common import PaginatedResult
from app.models.job import JobCandidate, JobRecord
from app.models.provider import ProviderCreate, ProviderRecord, ProviderUpdate
from app.models.provider_run import ProviderRunCreate, ProviderRunRecord, ProviderRunUpdate
from app.models.search import SearchCreate, SearchRecord, SearchUpdate


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


class ProviderRepository(Protocol):
    """Persistence operations required for provider registrations."""

    def get(self, provider_id: UUID) -> ProviderRecord | None:
        """Return a provider by ID when it exists."""

    def create(self, provider: ProviderCreate, now: datetime) -> ProviderRecord:
        """Persist a provider registration."""

    def update(
        self,
        provider_id: UUID,
        changes: ProviderUpdate,
        now: datetime,
    ) -> ProviderRecord | None:
        """Apply mutable provider settings."""

    def list(self, offset: int, limit: int) -> PaginatedResult[ProviderRecord]:
        """Return registered providers ordered by display name."""

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
