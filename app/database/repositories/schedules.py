"""SQLite persistence for recurring schedules and their dispatch history."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func
from sqlmodel import Session, select

from app.database.mappers import to_schedule_record, to_schedule_run_record
from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.tables import ScheduleRunTable, ScheduleTable
from app.models.common import PaginatedResult
from app.models.schedule import (
    ScheduleCreate,
    ScheduleRecord,
    ScheduleRunRecord,
    ScheduleRunStatus,
    ScheduleUpdate,
)


class SqliteScheduleRepository:
    """Persist schedule definitions and small, newest-first dispatch histories."""

    def __init__(self, session: Session) -> None:
        """Create a repository backed by one short-lived database session."""

        self._session = session

    def get(self, schedule_id: UUID) -> ScheduleRecord | None:
        """Return one schedule when it exists."""

        table = self._session.get(ScheduleTable, schedule_id)
        return to_schedule_record(table) if table else None

    def create(self, schedule: ScheduleCreate, now: datetime) -> ScheduleRecord:
        """Persist one schedule definition."""

        table = ScheduleTable(
            name=schedule.name,
            search_id=schedule.search_id,
            trigger_type=schedule.trigger_type.value,
            daily_time=schedule.daily_time,
            cron_expression=schedule.cron_expression,
            enabled=schedule.enabled,
            incremental=schedule.incremental,
            retry_limit=schedule.retry_limit,
            created_at=now,
            updated_at=now,
        )
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_schedule_record(table)

    def update(
        self,
        schedule_id: UUID,
        changes: ScheduleUpdate,
        now: datetime,
    ) -> ScheduleRecord | None:
        """Persist explicitly supplied mutable schedule fields."""

        table = self._session.get(ScheduleTable, schedule_id)
        if table is None:
            return None
        values = changes.model_dump(exclude_unset=True)
        for field_name in (
            "name",
            "daily_time",
            "cron_expression",
            "enabled",
            "incremental",
            "retry_limit",
        ):
            if field_name in values:
                setattr(table, field_name, values[field_name])
        if "trigger_type" in values:
            table.trigger_type = values["trigger_type"].value
        table.updated_at = now
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_schedule_record(table)

    def list(self, offset: int, limit: int) -> PaginatedResult[ScheduleRecord]:
        """Return schedules in a bounded name-ordered page."""

        statement = select(ScheduleTable).order_by(ScheduleTable.name, ScheduleTable.id)
        tables = self._session.exec(statement.offset(offset).limit(limit)).all()
        total = self._session.exec(select(func.count()).select_from(ScheduleTable)).one()
        return PaginatedResult(
            items=[to_schedule_record(table) for table in tables],
            total=total,
            offset=offset,
            limit=limit,
        )

    def delete(self, schedule_id: UUID) -> bool:
        """Delete one schedule while preserving its run history."""

        table = self._session.get(ScheduleTable, schedule_id)
        if table is None:
            return False
        self._session.delete(table)
        commit_or_raise_conflict(self._session)
        return True

    def create_run(
        self,
        schedule_id: UUID,
        search_id: UUID,
        attempt: int,
        manual: bool,
        now: datetime,
    ) -> ScheduleRunRecord:
        """Create one pending dispatch-history row before provider work is queued."""

        table = ScheduleRunTable(
            schedule_id=schedule_id,
            search_id=search_id,
            attempt=attempt,
            manual=manual,
            created_at=now,
        )
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_schedule_run_record(table)

    def finish_run(
        self,
        run_id: UUID,
        status: ScheduleRunStatus,
        provider_run_count: int,
        failed_provider_count: int,
        error_summary: str | None,
        now: datetime,
    ) -> ScheduleRunRecord | None:
        """Store the safe dispatch outcome and completion timestamp."""

        table = self._session.get(ScheduleRunTable, run_id)
        if table is None:
            return None
        table.status = status.value
        table.provider_run_count = provider_run_count
        table.failed_provider_count = failed_provider_count
        table.error_summary = error_summary
        table.finished_at = now
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_schedule_run_record(table)

    def mark_dispatched(self, schedule_id: UUID, now: datetime) -> None:
        """Record the latest dispatch time used as incremental-run metadata."""

        table = self._session.get(ScheduleTable, schedule_id)
        if table is not None:
            table.last_dispatched_at = now
            table.updated_at = now
            self._session.add(table)
            commit_or_raise_conflict(self._session)

    def list_runs(
        self, schedule_id: UUID, offset: int, limit: int
    ) -> PaginatedResult[ScheduleRunRecord]:
        """Return bounded newest-first durable dispatch history for one schedule."""

        statement = select(ScheduleRunTable).where(ScheduleRunTable.schedule_id == schedule_id)
        count = (
            select(func.count())
            .select_from(ScheduleRunTable)
            .where(ScheduleRunTable.schedule_id == schedule_id)
        )
        tables = self._session.exec(
            statement.order_by(desc(ScheduleRunTable.created_at), desc(ScheduleRunTable.id))
            .offset(offset)
            .limit(limit)
        ).all()
        total = self._session.exec(count).one()
        return PaginatedResult(
            items=[to_schedule_run_record(table) for table in tables],
            total=total,
            offset=offset,
            limit=limit,
        )
