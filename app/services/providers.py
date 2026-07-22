"""Application service for provider configuration lifecycle."""

from __future__ import annotations

from uuid import UUID

from app.models.common import PaginatedResult, utc_now
from app.models.errors import EntityNotFoundError
from app.models.provider import ProviderCreate, ProviderRecord, ProviderUpdate
from app.services.ports import ProviderRepository


class ProviderService:
    """Coordinate provider configuration without knowing provider implementations."""

    def __init__(self, repository: ProviderRepository) -> None:
        """Create the service with a provider registration repository."""

        self._repository = repository

    def create(self, provider: ProviderCreate) -> ProviderRecord:
        """Register a provider configuration."""

        return self._repository.create(provider, utc_now())

    def get(self, provider_id: UUID) -> ProviderRecord:
        """Return a provider registration or raise a missing-resource error."""

        provider = self._repository.get(provider_id)
        if provider is None:
            raise EntityNotFoundError("Provider", provider_id)
        return provider

    def list(self, offset: int, limit: int) -> PaginatedResult[ProviderRecord]:
        """Return a bounded page of registered providers."""

        return self._repository.list(offset, limit)

    def update(self, provider_id: UUID, changes: ProviderUpdate) -> ProviderRecord:
        """Update mutable provider settings or raise a missing-resource error."""

        provider = self._repository.update(provider_id, changes, utc_now())
        if provider is None:
            raise EntityNotFoundError("Provider", provider_id)
        return provider

    def delete(self, provider_id: UUID) -> None:
        """Delete a provider configuration or raise a missing-resource error."""

        if not self._repository.delete(provider_id):
            raise EntityNotFoundError("Provider", provider_id)
