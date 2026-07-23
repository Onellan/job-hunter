"""Application service for provider configuration lifecycle."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from app.models.common import PaginatedResult, utc_now
from app.models.errors import EntityNotFoundError
from app.models.provider import (
    ProviderAvailabilityReason,
    ProviderCreate,
    ProviderDefinition,
    ProviderRecord,
    ProviderUpdate,
)
from app.services.ports import ProviderRepository


class ProviderService:
    """Coordinate provider configuration without knowing provider implementations."""

    def __init__(
        self,
        repository: ProviderRepository,
        availability_by_code: Mapping[str, ProviderAvailabilityReason | None] | None = None,
    ) -> None:
        """Create the service with a provider registration repository."""

        self._repository = repository
        self._availability_by_code = availability_by_code or {}

    def create(self, provider: ProviderCreate) -> ProviderRecord:
        """Register a provider configuration."""

        return self._with_availability(self._repository.create(provider, utc_now()))

    def bootstrap(self, definitions: Sequence[ProviderDefinition]) -> None:
        """Create discovered default rows once without changing existing provider settings."""

        self._repository.create_missing(
            [definition.as_create() for definition in definitions], utc_now()
        )

    def get(self, provider_id: UUID) -> ProviderRecord:
        """Return a provider registration or raise a missing-resource error."""

        provider = self._repository.get(provider_id)
        if provider is None:
            raise EntityNotFoundError("Provider", provider_id)
        return self._with_availability(provider)

    def list(self, offset: int, limit: int) -> PaginatedResult[ProviderRecord]:
        """Return a bounded page of registered providers."""

        page = self._repository.list(offset, limit)
        return page.model_copy(
            update={"items": [self._with_availability(item) for item in page.items]}
        )

    def update(self, provider_id: UUID, changes: ProviderUpdate) -> ProviderRecord:
        """Update mutable provider settings or raise a missing-resource error."""

        provider = self._repository.update(provider_id, changes, utc_now())
        if provider is None:
            raise EntityNotFoundError("Provider", provider_id)
        return self._with_availability(provider)

    def delete(self, provider_id: UUID) -> None:
        """Delete a provider configuration or raise a missing-resource error."""

        if not self._repository.delete(provider_id):
            raise EntityNotFoundError("Provider", provider_id)

    def _with_availability(self, provider: ProviderRecord) -> ProviderRecord:
        """Attach a transient safe runtime status without persisting it."""

        return provider.model_copy(
            update={"availability_reason": self._availability_by_code.get(provider.code)}
        )
