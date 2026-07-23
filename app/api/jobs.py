"""Versioned JSON endpoints for durable provider-neutral jobs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import (
    get_job_scoring_service,
    get_job_service,
    get_job_workspace_service,
    get_resume_matching_service,
)
from app.models.common import PaginatedResult
from app.models.job import (
    JobCandidate,
    JobRecord,
    JobUpdate,
    JobUpsertResult,
    ProviderCode,
    WorkplaceType,
)
from app.models.matching import JobComparisonRequest, JobComparisonResult
from app.models.scoring import JobScoreResult
from app.models.workspace import (
    BulkJobWorkflowResult,
    BulkJobWorkflowUpdate,
    JobSort,
    JobWorkflowRecord,
    JobWorkflowUpdate,
    JobWorkspaceItem,
    JobWorkspaceQuery,
)
from app.services.jobs import JobService
from app.services.matching import ResumeMatchingService
from app.services.scoring import JobScoringService
from app.services.workspace import JobWorkspaceService

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


@router.get("/workspace", response_model=PaginatedResult[JobWorkspaceItem])
def list_job_workspace(
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
    text: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    source: Annotated[ProviderCode | None, Query()] = None,
    workplace_type: Annotated[WorkplaceType | None, Query()] = None,
    bookmarked: bool | None = None,
    applied: bool | None = None,
    sort: JobSort = JobSort.RECENT,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PaginatedResult[JobWorkspaceItem]:
    """Return searchable job results paired with their user workflow state."""

    return service.list(
        JobWorkspaceQuery(
            text=text,
            source=source,
            workplace_type=workplace_type,
            bookmarked=bookmarked,
            applied=applied,
            sort=sort,
            offset=offset,
            limit=limit,
        )
    )


@router.post("/workflow/bulk", response_model=BulkJobWorkflowResult)
def bulk_update_job_workflow(
    request: BulkJobWorkflowUpdate,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
) -> BulkJobWorkflowResult:
    """Apply one reversible workflow action to a bounded selected-job set."""

    return service.bulk_update_workflow(request)


@router.get("/{job_id}/score", response_model=JobScoreResult)
def score_job(
    job_id: UUID,
    service: Annotated[JobScoringService, Depends(get_job_scoring_service)],
) -> JobScoreResult:
    """Return a current deterministic, explainable score for one persisted job."""

    return service.score_job(job_id)


@router.post("/compare", response_model=JobComparisonResult)
def compare_jobs(
    request: JobComparisonRequest,
    service: Annotated[ResumeMatchingService, Depends(get_resume_matching_service)],
) -> JobComparisonResult:
    """Compare two or three current jobs against the consented local resume profile."""

    return service.compare(request)


@router.get("/{job_id}", response_model=JobRecord)
def get_job(
    job_id: UUID,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRecord:
    """Return one durable job."""

    return service.get(job_id)


@router.get("/{job_id}/workspace", response_model=JobWorkspaceItem)
def get_workspace_job(
    job_id: UUID,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
) -> JobWorkspaceItem:
    """Return a job with user-managed workflow state for a detail screen."""

    return service.get(job_id)


@router.patch("/{job_id}/workflow", response_model=JobWorkflowRecord)
def update_job_workflow(
    job_id: UUID,
    changes: JobWorkflowUpdate,
    service: Annotated[JobWorkspaceService, Depends(get_job_workspace_service)],
) -> JobWorkflowRecord:
    """Update bookmarks, application state, or notes without changing job source data."""

    return service.update_workflow(job_id, changes)


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
