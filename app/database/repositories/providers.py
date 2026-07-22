"""SQLite repository implementation for provider registrations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from app.database.mappers import to_provider_record
from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.tables import ProviderTable
from app.models.common import PaginatedResult
from app.models.provider import ProviderCreate, ProviderRecord, ProviderUpdate


class SqliteProviderRepository:
    """Persist provider enablement and non-secret provider configuration."""

    def __init__(self, session: Session) -> None:
        """Create a repository backed by one request-scoped session."""

        self._session = session

    def get(self, provider_id: UUID) -> ProviderRecord | None:
        """Return a provider registration by ID when it exists."""

        table = self._session.get(ProviderTable, provider_id)
        return to_provider_record(table) if table else None

    def create(self, provider: ProviderCreate, now: datetime) -> ProviderRecord:
        """Persist a provider registration."""

        table = ProviderTable(
            code=provider.code,
            display_name=provider.display_name,
            enabled=provider.enabled,
            configuration=provider.model_dump(mode="json")["configuration"],
            created_at=now,
            updated_at=now,
        )
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_provider_record(table)

    def update(
        self,
        provider_id: UUID,
        changes: ProviderUpdate,
        now: datetime,
    ) -> ProviderRecord | None:
        """Apply explicit non-null mutable provider fields."""

        table = self._session.get(ProviderTable, provider_id)
        if table is None:
            return None

        values = changes.model_dump(exclude_unset=True, mode="json")
        if values.get("display_name") is not None:
            table.display_name = values["display_name"]
        if values.get("enabled") is not None:
            table.enabled = values["enabled"]
        if values.get("configuration") is not None:
            table.configuration = values["configuration"]
        table.updated_at = now
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_provider_record(table)

    def list(self, offset: int, limit: int) -> PaginatedResult[ProviderRecord]:
        """Return providers in a bounded page ordered by display name."""

        statement = select(ProviderTable).order_by(ProviderTable.display_name, ProviderTable.id)
        tables = self._session.exec(statement.offset(offset).limit(limit)).all()
        total = self._session.exec(select(func.count()).select_from(ProviderTable)).one()
        return PaginatedResult(
            items=[to_provider_record(table) for table in tables],
            total=total,
            offset=offset,
            limit=limit,
        )

    def delete(self, provider_id: UUID) -> bool:
        """Delete a provider registration when no execution history references it."""

        table = self._session.get(ProviderTable, provider_id)
        if table is None:
            return False
        self._session.delete(table)
        commit_or_raise_conflict(self._session)
        return True
