"""Versioned JSON endpoints for durable provider-neutral jobs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_job_service
from app.models.common import PaginatedResult
from app.models.job import JobCandidate, JobRecord, JobUpdate, JobUpsertResult
from app.services.jobs import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobUpsertResult, status_code=status.HTTP_201_CREATED)
def upsert_job(
    candidate: JobCandidate,
    response: Response,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobUpsertResult:
    """Create a job or refresh its latest data when it is already known."""

    result = service.upsert(candidate)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return result


@router.get("", response_model=PaginatedResult[JobRecord])
def list_jobs(
    service: Annotated[JobService, Depends(get_job_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    source: Annotated[str | None, Query(min_length=2, max_length=64)] = None,
) -> PaginatedResult[JobRecord]:
    """Return a bounded latest-observation-first page of durable jobs."""

    return service.list(offset, limit, source)


@router.get("/{job_id}", response_model=JobRecord)
def get_job(
    job_id: UUID,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRecord:
    """Return one durable job."""

    return service.get(job_id)


@router.patch("/{job_id}", response_model=JobRecord)
def update_job(
    job_id: UUID,
    changes: JobUpdate,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRecord:
    """Update mutable job data without changing durable source identity."""

    return service.update(job_id, changes)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: UUID,
    service: Annotated[JobService, Depends(get_job_service)],
) -> Response:
    """Delete one durable job."""

    service.delete(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
