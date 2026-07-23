"""Shared parameterised predicates and allow-listed ordering for job reads."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import ColumnElement, desc, or_

from app.database.tables import JobTable, JobWorkflowTable
from app.models.export import JobExportScope
from app.models.workspace import JobSort, JobWorkspaceQuery


def workspace_conditions(
    query: JobWorkspaceQuery | JobExportScope,
) -> list[ColumnElement[bool]]:
    """Build SQLite predicates shared by workspace pages and exports."""

    conditions: list[ColumnElement[bool]] = []
    if query.text:
        pattern = f"%{query.text}%"
        conditions.append(
            or_(
                JobTable.title.ilike(pattern),
                JobTable.company.ilike(pattern),
                JobTable.location.ilike(pattern),
            )
        )
    if query.source:
        conditions.append(JobTable.source == query.source)
    if query.workplace_type:
        conditions.append(JobTable.workplace_type == query.workplace_type.value)
    if getattr(query, "location", None):
        conditions.append(JobTable.location.ilike(f"%{query.location}%"))
    if getattr(query, "employment_type", None):
        conditions.append(JobTable.employment_type == query.employment_type.value)
    if getattr(query, "posted_within_days", None):
        conditions.append(
            JobTable.published_at >= datetime.now(UTC) - timedelta(days=query.posted_within_days)
        )
    if query.bookmarked is not None:
        conditions.append(_workflow_boolean_condition("is_bookmarked", query.bookmarked))
    if query.applied is not None:
        conditions.append(_workflow_boolean_condition("is_applied", query.applied))
    return conditions


def apply_job_sort(statement: object, sort: JobSort) -> object:
    """Apply an allow-listed sort rather than accepting user-provided SQL names."""

    sort_fields = {
        JobSort.RECENT: (desc(JobTable.last_seen_at), desc(JobTable.id)),
        JobSort.PUBLISHED: (
            JobTable.published_at.is_(None),
            desc(JobTable.published_at),
            desc(JobTable.id),
        ),
        JobSort.TITLE: (JobTable.title, JobTable.id),
        JobSort.COMPANY: (JobTable.company.is_(None), JobTable.company, JobTable.id),
    }
    return statement.order_by(*sort_fields[sort])  # type: ignore[union-attr]


def _workflow_boolean_condition(field_name: str, expected: bool) -> ColumnElement[bool]:
    """Treat a missing lazy workflow row as false for filters."""

    field = getattr(JobWorkflowTable, field_name)
    if expected:
        return field.is_(True)
    return or_(JobWorkflowTable.job_id.is_(None), field.is_(False))
