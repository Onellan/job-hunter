"""Conversion from persistence tables to provider-neutral read contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.database.tables import JobTable, ProviderRunTable, ProviderTable, SearchTable
from app.models.job import JobRecord
from app.models.provider import ProviderRecord
from app.models.provider_run import ProviderRunRecord
from app.models.search import SearchCriteria, SearchRecord


def to_job_record(table: JobTable) -> JobRecord:
    """Convert one job table row into a timezone-normalised domain record."""

    payload = table.model_dump()
    _normalise_timestamps(payload)
    return JobRecord.model_validate(payload)


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
