"""Base contract implemented by every job provider plugin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import ClassVar

from pydantic import JsonValue

from app.models.job import JobCandidate
from app.models.provider import ProviderAvailabilityReason, ProviderDefinition
from app.models.search import SearchCriteria


class BaseProvider(ABC):
    """Acquire and normalise jobs without knowing persistence or presentation."""

    code: ClassVar[str]
    display_name: ClassVar[str]
    default_enabled: ClassVar[bool] = True
    bootstrap_by_default: ClassVar[bool] = False

    @classmethod
    def default_configuration(cls) -> dict[str, JsonValue]:
        """Return a fresh non-secret configuration used only for a missing provider row."""

        return {}

    @classmethod
    def availability_reason(cls) -> ProviderAvailabilityReason | None:
        """Return a safe local dependency category without contacting a provider."""

        return None

    @classmethod
    def definition(cls) -> ProviderDefinition:
        """Build the validated discovery-owned defaults for this provider."""

        return ProviderDefinition(
            code=cls.code,
            display_name=cls.display_name,
            enabled=cls.default_enabled,
            configuration=cls.default_configuration(),
            availability_reason=cls.availability_reason(),
            bootstrap=cls.bootstrap_by_default,
        )

    @abstractmethod
    def search(
        self,
        criteria: SearchCriteria,
        configuration: Mapping[str, JsonValue],
    ) -> Iterable[JobCandidate]:
        """Return standard job candidates for one provider search.

        Args:
            criteria: Provider-neutral saved-search criteria.
            configuration: Non-secret provider-specific configuration.

        Returns:
            A bounded iterable of normalised job candidates.

        Raises:
            ProviderError: When an expected provider-boundary failure occurs.
        """
