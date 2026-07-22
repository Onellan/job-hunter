"""Versioned JSON endpoints for provider registrations."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_provider_service
from app.models.common import PaginatedResult
from app.models.provider import ProviderCreate, ProviderRecord, ProviderUpdate
from app.services.providers import ProviderService

router = APIRouter(prefix="/providers", tags=["providers"])


@router.post("", response_model=ProviderRecord, status_code=status.HTTP_201_CREATED)
def create_provider(
    provider: ProviderCreate,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderRecord:
    """Register a provider configuration without loading its implementation."""

    return service.create(provider)


@router.get("", response_model=PaginatedResult[ProviderRecord])
def list_providers(
    service: Annotated[ProviderService, Depends(get_provider_service)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PaginatedResult[ProviderRecord]:
    """Return a bounded page of registered providers."""

    return service.list(offset, limit)


@router.get("/{provider_id}", response_model=ProviderRecord)
def get_provider(
    provider_id: UUID,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderRecord:
    """Return one provider registration."""

    return service.get(provider_id)


@router.patch("/{provider_id}", response_model=ProviderRecord)
def update_provider(
    provider_id: UUID,
    changes: ProviderUpdate,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderRecord:
    """Update mutable provider settings."""

    return service.update(provider_id, changes)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(
    provider_id: UUID,
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> Response:
    """Delete a provider without execution history references."""

    service.delete(provider_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
