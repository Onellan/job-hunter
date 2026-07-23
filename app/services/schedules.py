"""Application use cases for durable recurring saved-search schedules."""

from __future__ import annotations

from uuid import UUID

from app.models.common import PaginatedResult, utc_now
from app.models.errors import EntityNotFoundError
from app.models.schedule import (
    ScheduleCreate,
    ScheduleRecord,
    ScheduleRunRecord,
    ScheduleRunStatus,
    ScheduleUpdate,
)
from app.services.ports import ScheduleRepository, SearchRepository


class ScheduleService:
    """Validate schedule references and coordinate durable schedule history."""

    def __init__(
        self, schedule_repository: ScheduleRepository, search_repository: SearchRepository
    ) -> None:
        """Create the service with persistence contracts only."""

        self._schedule_repository = schedule_repository
        self._search_repository = search_repository

    def create(self, schedule: ScheduleCreate) -> ScheduleRecord:
        """Create a schedule for an existing saved search."""

        self._get_search(schedule.search_id)
        return self._schedule_repository.create(schedule, utc_now())

    def get(self, schedule_id: UUID) -> ScheduleRecord:
        """Return one schedule or raise a missing-resource error."""

        schedule = self._schedule_repository.get(schedule_id)
        if schedule is None:
            raise EntityNotFoundError("Schedule", schedule_id)
        return schedule

    def list(self, offset: int, limit: int) -> PaginatedResult[ScheduleRecord]:
        """Return a bounded page of recurring schedules."""

        return self._schedule_repository.list(offset, limit)

    def update(self, schedule_id: UUID, changes: ScheduleUpdate) -> ScheduleRecord:
        """Persist mutable schedule fields after validating the resulting trigger."""

        current = self.get(schedule_id)
        merged = current.model_dump(
            exclude={"id", "last_dispatched_at", "created_at", "updated_at"}
        )
        merged.update(changes.model_dump(exclude_unset=True))
        validated = ScheduleCreate.model_validate(merged)
        updated = self._schedule_repository.update(
            schedule_id,
            ScheduleUpdate.model_validate(validated.model_dump()),
            utc_now(),
        )
        if updated is None:
            raise EntityNotFoundError("Schedule", schedule_id)
        return updated

    def delete(self, schedule_id: UUID) -> None:
        """Delete a schedule while leaving its historical run rows intact."""

        if not self._schedule_repository.delete(schedule_id):
            raise EntityNotFoundError("Schedule", schedule_id)

    def start_run(self, schedule_id: UUID, attempt: int, manual: bool) -> ScheduleRunRecord:
        """Create a run-history record before handing work to provider execution."""

        schedule = self.get(schedule_id)
        return self._schedule_repository.create_run(
            schedule.id, schedule.search_id, attempt, manual, utc_now()
        )

    def finish_run(
        self,
        run_id: UUID,
        status: ScheduleRunStatus,
        provider_run_count: int,
        failed_provider_count: int,
        error_summary: str | None,
    ) -> ScheduleRunRecord:
        """Complete one dispatch-history record with safe operational metadata."""

        updated = self._schedule_repository.finish_run(
            run_id,
            status,
            provider_run_count,
            failed_provider_count,
            error_summary,
            utc_now(),
        )
        if updated is None:
            raise EntityNotFoundError("Schedule run", run_id)
        return updated

    def mark_dispatched(self, schedule_id: UUID) -> None:
        """Store incremental-execution metadata after a successful dispatch."""

        self._schedule_repository.mark_dispatched(schedule_id, utc_now())

    def list_runs(
        self, schedule_id: UUID, offset: int, limit: int
    ) -> PaginatedResult[ScheduleRunRecord]:
        """Return durable execution history after checking the schedule exists."""

        self.get(schedule_id)
        return self._schedule_repository.list_runs(schedule_id, offset, limit)

    def _get_search(self, search_id: UUID) -> None:
        """Ensure a schedule cannot point to a missing saved search."""

        if self._search_repository.get(search_id) is None:
            raise EntityNotFoundError("Search", search_id)
