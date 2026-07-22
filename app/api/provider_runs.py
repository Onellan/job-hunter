"""Versioned JSON endpoints for provider execution history."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_provider_run_service
from app.models.common import PaginatedResult
from app.models.provider_run import ProviderRunCreate, ProviderRunRecord, ProviderRunUpdate
from app.services.provider_runs import ProviderRunService

router = APIRouter(prefix="/provider-runs", tags=["provider-runs"])


@router.post("", response_model=ProviderRunRecord, status_code=status.HTTP_201_CREATED)
def create_provider_run(
    provider_run: ProviderRunCreate,
    service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
) -> ProviderRunRecord:
    """Create a pending provider run with validated durable references."""

    return service.create(provider_run)


@router.get("", response_model=PaginatedResult[ProviderRunRecord])
def list_provider_runs(
    service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    provider_id: UUID | None = None,
    search_id: UUID | None = None,
) -> PaginatedResult[ProviderRunRecord]:
    """Return a bounded page of durable provider runs."""

    return service.list(offset, limit, provider_id, search_id)


@router.get("/{run_id}", response_model=ProviderRunRecord)
def get_provider_run(
    run_id: UUID,
    service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
) -> ProviderRunRecord:
    """Return one provider run."""

    return service.get(run_id)


@router.patch("/{run_id}", response_model=ProviderRunRecord)
def update_provider_run(
    run_id: UUID,
    changes: ProviderRunUpdate,
    service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
) -> ProviderRunRecord:
    """Update provider-run status and safe outcome metadata."""

    return service.update(run_id, changes)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider_run(
    run_id: UUID,
    service: Annotated[ProviderRunService, Depends(get_provider_run_service)],
) -> Response:
    """Delete one provider execution-history record."""

    service.delete(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
