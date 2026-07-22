"""Application service for provider-run lifecycle and transitions."""

from __future__ import annotations

import logging
from uuid import UUID

from app.models.common import PaginatedResult, utc_now
from app.models.errors import EntityNotFoundError
from app.models.provider_run import (
    ProviderRunCreate,
    ProviderRunRecord,
    ProviderRunStatus,
    ProviderRunUpdate,
    validate_provider_run_transition,
)
from app.services.ports import ProviderRepository, ProviderRunRepository, SearchRepository

logger = logging.getLogger(__name__)

_TERMINAL_RUN_STATUSES = frozenset(
    {
        ProviderRunStatus.SUCCEEDED,
        ProviderRunStatus.FAILED,
        ProviderRunStatus.CANCELLED,
    }
)


class ProviderRunService:
    """Coordinate durable provider execution records and lifecycle validity."""

    def __init__(
        self,
        provider_repository: ProviderRepository,
        search_repository: SearchRepository,
        run_repository: ProviderRunRepository,
    ) -> None:
        """Create the service with repositories needed to validate references."""

        self._provider_repository = provider_repository
        self._search_repository = search_repository
        self._run_repository = run_repository

    def create(self, provider_run: ProviderRunCreate) -> ProviderRunRecord:
        """Create a pending run after validating its durable references."""

        self._get_provider(provider_run.provider_id)
        if provider_run.search_id is not None:
            self._get_search(provider_run.search_id)
        run = self._run_repository.create(provider_run, utc_now())
        logger.info("provider_run_created", extra={"provider_run_id": str(run.id)})
        return run

    def get(self, run_id: UUID) -> ProviderRunRecord:
        """Return a provider run or raise a missing-resource error."""

        run = self._run_repository.get(run_id)
        if run is None:
            raise EntityNotFoundError("Provider run", run_id)
        return run

    def list(
        self,
        offset: int,
        limit: int,
        provider_id: UUID | None,
        search_id: UUID | None,
    ) -> PaginatedResult[ProviderRunRecord]:
        """Return a bounded page of provider runs filtered by durable references."""

        return self._run_repository.list(offset, limit, provider_id, search_id)

    def update(self, run_id: UUID, changes: ProviderRunUpdate) -> ProviderRunRecord:
        """Apply an allowed lifecycle transition and record automatic timestamps."""

        current = self.get(run_id)
        requested_status = changes.status or current.status
        validate_provider_run_transition(current.status, requested_status)
        timestamp = utc_now()
        started_at = current.started_at
        finished_at = current.finished_at
        if requested_status == ProviderRunStatus.RUNNING and started_at is None:
            started_at = timestamp
        if requested_status in _TERMINAL_RUN_STATUSES and finished_at is None:
            finished_at = timestamp

        updated = self._run_repository.update(
            run_id,
            changes,
            started_at,
            finished_at,
            timestamp,
        )
        if updated is None:
            raise EntityNotFoundError("Provider run", run_id)
        logger.info(
            "provider_run_updated",
            extra={
                "provider_run_id": str(updated.id),
                "status": updated.status,
                "result_count": updated.result_count,
            },
        )
        return updated

    def delete(self, run_id: UUID) -> None:
        """Delete a provider run or raise a missing-resource error."""

        if not self._run_repository.delete(run_id):
            raise EntityNotFoundError("Provider run", run_id)

    def _get_provider(self, provider_id: UUID) -> None:
        """Ensure a provider ID exists without leaking repository details."""

        if self._provider_repository.get(provider_id) is None:
            raise EntityNotFoundError("Provider", provider_id)

    def _get_search(self, search_id: UUID) -> None:
        """Ensure an optional saved-search ID exists before a run is created."""

        if self._search_repository.get(search_id) is None:
            raise EntityNotFoundError("Search", search_id)
