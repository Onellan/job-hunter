"""Base contract implemented by every job provider plugin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import ClassVar

from pydantic import JsonValue

from app.models.job import JobCandidate
from app.models.search import SearchCriteria


class BaseProvider(ABC):
    """Acquire and normalise jobs without knowing persistence or presentation."""

    code: ClassVar[str]
    display_name: ClassVar[str]

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
