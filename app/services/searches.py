"""Application service for saved-search lifecycle."""

from __future__ import annotations

from uuid import UUID

from app.models.common import PaginatedResult, utc_now
from app.models.errors import EntityNotFoundError
from app.models.search import SearchCreate, SearchRecord, SearchUpdate
from app.services.ports import SearchRepository


class SearchService:
    """Coordinate durable search definitions without provider execution logic."""

    def __init__(self, repository: SearchRepository) -> None:
        """Create the service with a saved-search repository."""

        self._repository = repository

    def create(self, search: SearchCreate) -> SearchRecord:
        """Persist a reusable search definition."""

        return self._repository.create(search, utc_now())

    def get(self, search_id: UUID) -> SearchRecord:
        """Return a saved search or raise a missing-resource error."""

        search = self._repository.get(search_id)
        if search is None:
            raise EntityNotFoundError("Search", search_id)
        return search

    def list(self, offset: int, limit: int) -> PaginatedResult[SearchRecord]:
        """Return a bounded page of saved searches."""

        return self._repository.list(offset, limit)

    def update(self, search_id: UUID, changes: SearchUpdate) -> SearchRecord:
        """Update a saved search or raise a missing-resource error."""

        search = self._repository.update(search_id, changes, utc_now())
        if search is None:
            raise EntityNotFoundError("Search", search_id)
        return search

    def delete(self, search_id: UUID) -> None:
        """Delete a saved search or raise a missing-resource error."""

        if not self._repository.delete(search_id):
            raise EntityNotFoundError("Search", search_id)
