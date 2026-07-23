"""SQLite read model and workflow persistence for the server-rendered workspace."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ColumnElement, desc, func
from sqlmodel import Session, select

from app.database.mappers import (
    to_job_workflow_record,
    to_job_workspace_item,
    to_search_record,
)
from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.repositories.job_query import apply_job_sort, workspace_conditions
from app.database.tables import (
    JobTable,
    JobWorkflowTable,
    ProviderRunTable,
    ProviderTable,
    SearchTable,
)
from app.models.common import PaginatedResult
from app.models.dashboard import DashboardSnapshot
from app.models.provider_run import ProviderRunStatus
from app.models.workspace import (
    JobWorkflowRecord,
    JobWorkflowUpdate,
    JobWorkspaceItem,
    JobWorkspaceQuery,
)

_DASHBOARD_SEARCH_LIMIT = 5
_DASHBOARD_JOB_LIMIT = 5


class SqliteJobWorkspaceRepository:
    """Query jobs and persist their small optional user workflow state."""

    def __init__(self, session: Session) -> None:
        """Create the workspace repository for a request-scoped session."""

        self._session = session

    def get(self, job_id: UUID) -> JobWorkspaceItem | None:
        """Return one job with an optional workflow row in a single query."""

        statement = (
            select(JobTable, JobWorkflowTable)
            .outerjoin(JobWorkflowTable, JobWorkflowTable.job_id == JobTable.id)
            .where(JobTable.id == job_id)
        )
        row = self._session.exec(statement).first()
        return to_job_workspace_item(*row) if row else None

    def list(self, query: JobWorkspaceQuery) -> PaginatedResult[JobWorkspaceItem]:
        """Return one filtered page without materialising the complete result set."""

        conditions = workspace_conditions(query)
        statement = select(JobTable, JobWorkflowTable).outerjoin(
            JobWorkflowTable, JobWorkflowTable.job_id == JobTable.id
        )
        count_statement = select(func.count()).select_from(JobTable).outerjoin(
            JobWorkflowTable, JobWorkflowTable.job_id == JobTable.id
        )
        if conditions:
            statement = statement.where(*conditions)
            count_statement = count_statement.where(*conditions)

        ordered_statement = apply_job_sort(statement, query.sort)
        rows = self._session.exec(ordered_statement.offset(query.offset).limit(query.limit)).all()
        total = self._session.exec(count_statement).one()
        return PaginatedResult(
            items=[to_job_workspace_item(*row) for row in rows],
            total=total,
            offset=query.offset,
            limit=query.limit,
        )

    def update_workflow(
        self,
        job_id: UUID,
        changes: JobWorkflowUpdate,
        now: datetime,
    ) -> JobWorkflowRecord | None:
        """Create or update one workflow row after confirming the job exists."""

        if self._session.get(JobTable, job_id) is None:
            return None
        workflow = self._session.get(JobWorkflowTable, job_id)
        if workflow is None:
            workflow = JobWorkflowTable(job_id=job_id, created_at=now, updated_at=now)
        _apply_workflow_changes(workflow, changes, now)
        self._session.add(workflow)
        commit_or_raise_conflict(self._session)
        self._session.refresh(workflow)
        return to_job_workflow_record(workflow)

    def bulk_update_workflow(
        self,
        job_ids: Sequence[UUID],
        changes: JobWorkflowUpdate,
        now: datetime,
    ) -> int:
        """Update present jobs in one short transaction without a result cache."""

        existing_ids = set(
            self._session.exec(select(JobTable.id).where(JobTable.id.in_(job_ids))).all()
        )
        if not existing_ids:
            return 0
        workflows = {
            workflow.job_id: workflow
            for workflow in self._session.exec(
                select(JobWorkflowTable).where(JobWorkflowTable.job_id.in_(existing_ids))
            ).all()
        }
        for job_id in existing_ids:
            workflow = workflows.get(job_id)
            if workflow is None:
                workflow = JobWorkflowTable(job_id=job_id, created_at=now, updated_at=now)
            _apply_workflow_changes(workflow, changes, now)
            self._session.add(workflow)
        commit_or_raise_conflict(self._session)
        return len(existing_ids)


class SqliteDashboardRepository:
    """Serve compact dashboard metrics from indexed durable records."""

    def __init__(self, session: Session) -> None:
        """Create the dashboard read repository for one request-scoped session."""

        self._session = session

    def get_snapshot(self, today_start: datetime) -> DashboardSnapshot:
        """Return the fixed-size data needed by the dashboard screen."""

        latest_rows = self._session.exec(
            select(JobTable, JobWorkflowTable)
            .outerjoin(JobWorkflowTable, JobWorkflowTable.job_id == JobTable.id)
            .order_by(desc(JobTable.last_seen_at), desc(JobTable.id))
            .limit(_DASHBOARD_JOB_LIMIT)
        ).all()
        searches = self._session.exec(
            select(SearchTable).order_by(desc(SearchTable.updated_at), desc(SearchTable.id)).limit(
                _DASHBOARD_SEARCH_LIMIT
            )
        ).all()
        last_run_at = self._session.exec(select(func.max(ProviderRunTable.finished_at))).one()
        return DashboardSnapshot(
            jobs_found_today=self._count(JobTable.first_seen_at >= today_start),
            last_run_at=_as_utc(last_run_at),
            provider_count=self._count(),
            enabled_provider_count=self._count(
                ProviderTable.enabled.is_(True),
                table=ProviderTable,
            ),
            error_count_today=self._count(
                ProviderRunTable.status == ProviderRunStatus.FAILED.value,
                ProviderRunTable.created_at >= today_start,
                table=ProviderRunTable,
            ),
            recent_searches=[to_search_record(search) for search in searches],
            latest_jobs=[to_job_workspace_item(*row) for row in latest_rows],
        )

    def _count(
        self,
        *conditions: ColumnElement[bool],
        table: type[JobTable] | type[ProviderTable] | type[ProviderRunTable] = JobTable,
    ) -> int:
        """Execute one scalar count with safe parameterised conditions."""

        statement = select(func.count()).select_from(table)
        if conditions:
            statement = statement.where(*conditions)
        return self._session.exec(statement).one()


def _apply_workflow_changes(
    workflow: JobWorkflowTable,
    changes: JobWorkflowUpdate,
    now: datetime,
) -> None:
    """Apply only explicitly supplied state fields and touch the update time."""

    if "is_bookmarked" in changes.model_fields_set:
        workflow.is_bookmarked = changes.is_bookmarked or False
    if "is_applied" in changes.model_fields_set:
        workflow.is_applied = changes.is_applied or False
    if "notes" in changes.model_fields_set:
        workflow.notes = changes.notes
    workflow.updated_at = now


def _as_utc(value: datetime | None) -> datetime | None:
    """Normalise SQLite's naive aggregate timestamp to explicit UTC."""

    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
