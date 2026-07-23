"""Versioned JSON endpoints for saved searches."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_manual_search_service, get_search_service
from app.models.common import PaginatedResult
from app.models.search import SearchCreate, SearchRecord, SearchUpdate
from app.models.search_execution import ManualSearchStartResult
from app.services.manual_searches import ManualSearchService
from app.services.searches import SearchService

router = APIRouter(prefix="/searches", tags=["searches"])


@router.post("", response_model=SearchRecord, status_code=status.HTTP_201_CREATED)
def create_search(
    search: SearchCreate,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchRecord:
    """Persist a reusable provider-neutral search definition."""

    return service.create(search)


@router.get("", response_model=PaginatedResult[SearchRecord])
def list_searches(
    service: Annotated[SearchService, Depends(get_search_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PaginatedResult[SearchRecord]:
    """Return a bounded page of saved searches."""

    return service.list(offset, limit)


@router.get("/{search_id}", response_model=SearchRecord)
def get_search(
    search_id: UUID,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchRecord:
    """Return one saved search definition."""

    return service.get(search_id)


@router.patch("/{search_id}", response_model=SearchRecord)
def update_search(
    search_id: UUID,
    changes: SearchUpdate,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchRecord:
    """Update mutable saved-search fields."""

    return service.update(search_id, changes)


@router.post(
    "/{search_id}/run", response_model=ManualSearchStartResult, status_code=status.HTTP_202_ACCEPTED
)
def start_manual_search(
    search_id: UUID,
    service: Annotated[ManualSearchService, Depends(get_manual_search_service)],
) -> ManualSearchStartResult:
    """Create provider runs and queue bounded background execution without waiting for scraping."""

    return service.start(search_id)


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_search(
    search_id: UUID,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> Response:
    """Delete a saved search while preserving historical provider-run records."""

    service.delete(search_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
