"""SQLite repository implementation for saved search definitions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from app.database.mappers import to_search_record
from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.tables import SearchTable
from app.models.common import PaginatedResult
from app.models.search import SearchCreate, SearchRecord, SearchUpdate


class SqliteSearchRepository:
    """Persist reusable provider-neutral search definitions."""

    def __init__(self, session: Session) -> None:
        """Create a repository backed by one request-scoped session."""

        self._session = session

    def get(self, search_id: UUID) -> SearchRecord | None:
        """Return a saved search by ID when it exists."""

        table = self._session.get(SearchTable, search_id)
        return to_search_record(table) if table else None

    def create(self, search: SearchCreate, now: datetime) -> SearchRecord:
        """Persist a saved search definition."""

        table = SearchTable(
            name=search.name,
            criteria=search.criteria.model_dump(mode="json"),
            enabled=search.enabled,
            created_at=now,
            updated_at=now,
        )
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_search_record(table)

    def update(self, search_id: UUID, changes: SearchUpdate, now: datetime) -> SearchRecord | None:
        """Apply explicit non-null mutable saved-search fields."""

        table = self._session.get(SearchTable, search_id)
        if table is None:
            return None

        values = changes.model_dump(exclude_unset=True, mode="json")
        if values.get("name") is not None:
            table.name = values["name"]
        if values.get("criteria") is not None:
            table.criteria = values["criteria"]
        if values.get("enabled") is not None:
            table.enabled = values["enabled"]
        table.updated_at = now
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_search_record(table)

    def list(self, offset: int, limit: int) -> PaginatedResult[SearchRecord]:
        """Return saved searches in a bounded page ordered by name."""

        statement = select(SearchTable).order_by(SearchTable.name, SearchTable.id)
        tables = self._session.exec(statement.offset(offset).limit(limit)).all()
        total = self._session.exec(select(func.count()).select_from(SearchTable)).one()
        return PaginatedResult(
            items=[to_search_record(table) for table in tables],
            total=total,
            offset=offset,
            limit=limit,
        )

    def delete(self, search_id: UUID) -> bool:
        """Delete a saved search while retaining historic provider runs."""

        table = self._session.get(SearchTable, search_id)
        if table is None:
            return False
        self._session.delete(table)
        commit_or_raise_conflict(self._session)
        return True
