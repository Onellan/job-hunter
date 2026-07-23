"""Contracts for bounded job exports and their durable audit trail."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import ProviderCode, WorkplaceType
from app.models.workspace import JobSort


class ExportFormat(StrEnum):
    """Supported delivery formats for durable Job-Hunter data."""

    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    SQLITE = "sqlite"


class JobExportScope(BaseModel):
    """Validated job filters used when no explicit selection is supplied."""

    text: str | None = Field(default=None, min_length=1, max_length=200)
    source: ProviderCode | None = None
    workplace_type: WorkplaceType | None = None
    bookmarked: bool | None = None
    applied: bool | None = None
    sort: JobSort = JobSort.RECENT


class JobExportRequest(JobExportScope):
    """A request for selected jobs or all jobs matching a bounded filter set."""

    format: ExportFormat
    job_ids: list[UUID] = Field(default_factory=list, max_length=100)


class ExportEventRecord(BaseModel):
    """A durable, privacy-minimised audit record for one export request."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    format: ExportFormat
    resource: str
    selected_job_count: int | None = Field(default=None, ge=0)
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ExportDownload:
    """A presentation-neutral file download produced without holding all bytes in RAM."""

    filename: str
    media_type: str
    content: Iterator[bytes]
