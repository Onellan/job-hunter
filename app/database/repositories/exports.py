"""Stream-safe SQLite reads and audit persistence for data exports."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.database.mappers import to_export_event_record, to_job_workspace_item
from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.repositories.job_query import apply_job_sort, workspace_conditions
from app.database.tables import ExportEventTable, JobTable, JobWorkflowTable
from app.models.common import PaginatedResult
from app.models.export import ExportEventRecord, ExportFormat, JobExportScope
from app.models.workspace import JobWorkspaceItem

_EXPORT_BATCH_SIZE = 100


class SqliteJobExportRepository:
    """Read jobs in fixed batches and persist export audit events."""

    def __init__(self, engine: Engine) -> None:
        """Create the repository with an engine, not a request-bound session."""

        self._engine = engine

    def count_jobs(self, scope: JobExportScope, job_ids: Sequence[UUID]) -> int:
        """Count selected or filtered jobs without loading their descriptions."""

        with Session(self._engine) as session:
            statement = select(func.count()).select_from(JobTable).outerjoin(
                JobWorkflowTable, JobWorkflowTable.job_id == JobTable.id
            )
            return session.exec(self._apply_scope(statement, scope, job_ids)).one()

    def iter_jobs(
        self,
        scope: JobExportScope,
        job_ids: Sequence[UUID],
    ) -> Iterator[JobWorkspaceItem]:
        """Yield selected or filtered jobs in bounded batches after the route returns."""

        with Session(self._engine) as session:
            offset = 0
            while True:
                statement = select(JobTable, JobWorkflowTable).outerjoin(
                    JobWorkflowTable, JobWorkflowTable.job_id == JobTable.id
                )
                scoped_statement = self._apply_scope(statement, scope, job_ids)
                rows = session.exec(
                    apply_job_sort(scoped_statement, scope.sort)
                    .offset(offset)
                    .limit(_EXPORT_BATCH_SIZE)
                ).all()
                if not rows:
                    return
                for row in rows:
                    yield to_job_workspace_item(*row)
                if job_ids or len(rows) < _EXPORT_BATCH_SIZE:
                    return
                offset += len(rows)

    def create_event(
        self,
        export_format: ExportFormat,
        resource: str,
        selected_job_count: int | None,
        now: datetime,
    ) -> ExportEventRecord:
        """Persist an audit event before download content starts streaming."""

        with Session(self._engine) as session:
            table = ExportEventTable(
                format=export_format.value,
                resource=resource,
                selected_job_count=selected_job_count,
                created_at=now,
            )
            session.add(table)
            commit_or_raise_conflict(session)
            session.refresh(table)
            return to_export_event_record(table)

    def list_events(self, offset: int, limit: int) -> PaginatedResult[ExportEventRecord]:
        """Return a compact newest-first page of durable export audit entries."""

        with Session(self._engine) as session:
            statement = select(ExportEventTable).order_by(
                desc(ExportEventTable.created_at), desc(ExportEventTable.id)
            )
            tables = session.exec(statement.offset(offset).limit(limit)).all()
            total = session.exec(select(func.count()).select_from(ExportEventTable)).one()
            return PaginatedResult(
                items=[to_export_event_record(table) for table in tables],
                total=total,
                offset=offset,
                limit=limit,
            )

    def _apply_scope(
        self,
        statement: object,
        scope: JobExportScope,
        job_ids: Sequence[UUID],
    ) -> object:
        """Prioritise explicit selected jobs; otherwise apply validated filters."""

        if job_ids:
            return statement.where(JobTable.id.in_(job_ids))  # type: ignore[union-attr]
        conditions = workspace_conditions(scope)
        return statement.where(*conditions) if conditions else statement  # type: ignore[union-attr]
