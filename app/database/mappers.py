"""Conversion from persistence tables to provider-neutral read contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.database.tables import (
    ExportEventTable,
    JobTable,
    JobWorkflowTable,
    NotificationDeliveryTable,
    ProviderRunTable,
    ProviderTable,
    ScheduleRunTable,
    ScheduleTable,
    SearchTable,
)
from app.models.export import ExportEventRecord
from app.models.job import JobRecord
from app.models.notification import NotificationDeliveryRecord
from app.models.provider import ProviderRecord
from app.models.provider_run import ProviderRunRecord
from app.models.schedule import ScheduleRecord, ScheduleRunRecord
from app.models.search import SearchCriteria, SearchRecord
from app.models.workspace import JobWorkflowRecord, JobWorkflowState, JobWorkspaceItem


def to_job_record(table: JobTable) -> JobRecord:
    """Convert one job table row into a timezone-normalised domain record."""

    payload = table.model_dump()
    _normalise_timestamps(payload)
    return JobRecord.model_validate(payload)


def to_export_event_record(table: ExportEventTable) -> ExportEventRecord:
    """Convert one export audit row to its timestamp-normalised domain contract."""

    payload = table.model_dump()
    _normalise_timestamps(payload)
    return ExportEventRecord.model_validate(payload)


def to_notification_delivery_record(
    table: NotificationDeliveryTable,
) -> NotificationDeliveryRecord:
    """Convert a delivery audit row into its privacy-minimised read contract."""

    payload = table.model_dump()
    _normalise_timestamps(payload)
    return NotificationDeliveryRecord.model_validate(payload)


def to_job_workflow_state(table: JobWorkflowTable | None) -> JobWorkflowState:
    """Convert optional persistence state into its no-row-is-false representation."""

    if table is None:
        return JobWorkflowState()
    return JobWorkflowState.model_validate(table.model_dump())


def to_job_workflow_record(table: JobWorkflowTable) -> JobWorkflowRecord:
    """Convert one persisted job workflow row to its domain record."""

    payload = table.model_dump()
    _normalise_timestamps(payload)
    return JobWorkflowRecord.model_validate(payload)


def to_job_workspace_item(
    job_table: JobTable,
    workflow_table: JobWorkflowTable | None,
) -> JobWorkspaceItem:
    """Combine a job and optional workflow row returned by one joined query."""

    return JobWorkspaceItem(
        job=to_job_record(job_table),
        workflow=to_job_workflow_state(workflow_table),
    )


def to_provider_record(table: ProviderTable) -> ProviderRecord:
    """Convert one provider table row into a domain record."""

    payload = table.model_dump()
    _normalise_timestamps(payload)
    return ProviderRecord.model_validate(payload)


def to_search_record(table: SearchTable) -> SearchRecord:
    """Convert one search table row into a domain record."""

    payload = table.model_dump()
    payload["criteria"] = SearchCriteria.model_validate(payload["criteria"])
    _normalise_timestamps(payload)
    return SearchRecord.model_validate(payload)


def to_provider_run_record(table: ProviderRunTable) -> ProviderRunRecord:
    """Convert one provider-run table row into a domain record."""

    payload = table.model_dump()
    _normalise_timestamps(payload)
    return ProviderRunRecord.model_validate(payload)


def to_schedule_record(table: ScheduleTable) -> ScheduleRecord:
    """Convert one schedule row into its provider-neutral contract."""

    payload = table.model_dump()
    _normalise_timestamps(payload)
    return ScheduleRecord.model_validate(payload)


def to_schedule_run_record(table: ScheduleRunTable) -> ScheduleRunRecord:
    """Convert one schedule-run row into its provider-neutral contract."""

    payload = table.model_dump()
    _normalise_timestamps(payload)
    return ScheduleRunRecord.model_validate(payload)


def _normalise_timestamps(payload: dict[str, Any]) -> None:
    """Ensure SQLite's naive datetime reads are represented as UTC externally."""

    for field_name in (
        "published_at",
        "first_seen_at",
        "last_seen_at",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
    ):
        value = payload.get(field_name)
        if isinstance(value, datetime):
            payload[field_name] = _as_utc(value)


def _as_utc(value: datetime) -> datetime:
    """Return a timestamp with an explicit UTC offset."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
