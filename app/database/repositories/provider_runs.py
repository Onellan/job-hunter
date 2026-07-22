"""SQLite repository implementation for durable provider-run state."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func
from sqlmodel import Session, select

from app.database.mappers import to_provider_run_record
from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.tables import ProviderRunTable
from app.models.common import PaginatedResult
from app.models.provider_run import ProviderRunCreate, ProviderRunRecord, ProviderRunUpdate


class SqliteProviderRunRepository:
    """Persist provider execution lifecycle and safe outcome metadata."""

    def __init__(self, session: Session) -> None:
        """Create a repository backed by one request-scoped session."""

        self._session = session

    def get(self, run_id: UUID) -> ProviderRunRecord | None:
        """Return a provider run by ID when it exists."""

        table = self._session.get(ProviderRunTable, run_id)
        return to_provider_run_record(table) if table else None

    def create(self, provider_run: ProviderRunCreate, now: datetime) -> ProviderRunRecord:
        """Persist a pending provider run."""

        table = ProviderRunTable(
            provider_id=provider_run.provider_id,
            search_id=provider_run.search_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_provider_run_record(table)

    def update(
        self,
        run_id: UUID,
        changes: ProviderRunUpdate,
        started_at: datetime | None,
        finished_at: datetime | None,
        now: datetime,
    ) -> ProviderRunRecord | None:
        """Apply a previously validated execution-state update."""

        table = self._session.get(ProviderRunTable, run_id)
        if table is None:
            return None

        if changes.status is not None:
            table.status = changes.status.value
        if changes.result_count is not None:
            table.result_count = changes.result_count
        if "error_category" in changes.model_fields_set:
            table.error_category = changes.error_category
        if "error_summary" in changes.model_fields_set:
            table.error_summary = changes.error_summary
        if started_at is not None:
            table.started_at = started_at
        if finished_at is not None:
            table.finished_at = finished_at
        table.updated_at = now
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_provider_run_record(table)

    def list(
        self,
        offset: int,
        limit: int,
        provider_id: UUID | None,
        search_id: UUID | None,
    ) -> PaginatedResult[ProviderRunRecord]:
        """Return provider runs in a bounded page ordered by newest creation."""

        statement = select(ProviderRunTable)
        count_statement = select(func.count()).select_from(ProviderRunTable)
        if provider_id is not None:
            statement = statement.where(ProviderRunTable.provider_id == provider_id)
            count_statement = count_statement.where(ProviderRunTable.provider_id == provider_id)
        if search_id is not None:
            statement = statement.where(ProviderRunTable.search_id == search_id)
            count_statement = count_statement.where(ProviderRunTable.search_id == search_id)

        statement = statement.order_by(desc(ProviderRunTable.created_at), desc(ProviderRunTable.id))
        tables = self._session.exec(statement.offset(offset).limit(limit)).all()
        total = self._session.exec(count_statement).one()
        return PaginatedResult(
            items=[to_provider_run_record(table) for table in tables],
            total=total,
            offset=offset,
            limit=limit,
        )

    def delete(self, run_id: UUID) -> bool:
        """Delete a provider run without exposing table operations to services."""

        table = self._session.get(ProviderRunTable, run_id)
        if table is None:
            return False
        self._session.delete(table)
        commit_or_raise_conflict(self._session)
        return True
