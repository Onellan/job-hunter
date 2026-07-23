"""Versioned JSON and download endpoints for low-memory data exports."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_export_service
from app.core.downloads import download_response
from app.models.common import PaginatedResult
from app.models.export import ExportEventRecord, ExportFormat, JobExportRequest
from app.models.job import ProviderCode, WorkplaceType
from app.models.workspace import JobSort
from app.services.exports import ExportService

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/jobs")
def export_jobs(
    service: Annotated[ExportService, Depends(get_export_service)],
    format: ExportFormat,
    job_ids: Annotated[list[UUID] | None, Query()] = None,
    text: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    source: Annotated[ProviderCode | None, Query()] = None,
    workplace_type: Annotated[WorkplaceType | None, Query()] = None,
    bookmarked: bool | None = None,
    applied: bool | None = None,
    sort: JobSort = JobSort.RECENT,
) -> StreamingResponse:
    """Download selected or filtered jobs as a streamed CSV, JSON, or XLSX file."""

    request = JobExportRequest(
        format=format,
        job_ids=job_ids or [],
        text=text,
        source=source,
        workplace_type=workplace_type,
        bookmarked=bookmarked,
        applied=applied,
        sort=sort,
    )
    return download_response(service.export_jobs(request))


@router.get("/sqlite")
def export_sqlite_backup(
    service: Annotated[ExportService, Depends(get_export_service)],
) -> StreamingResponse:
    """Download a consistent file-backed SQLite database backup."""

    return download_response(service.export_sqlite_backup())


@router.get("/events", response_model=PaginatedResult[ExportEventRecord])
def list_export_events(
    service: Annotated[ExportService, Depends(get_export_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PaginatedResult[ExportEventRecord]:
    """Return a bounded export audit history without exposing download contents."""

    return service.list_events(offset, limit)
