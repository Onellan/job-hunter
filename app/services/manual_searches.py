"""Application service for non-blocking manual saved-search execution."""

from __future__ import annotations

import logging
from uuid import UUID

from app.models.errors import NoEnabledProviderError
from app.models.provider_run import ProviderRunCreate, ProviderRunStatus, ProviderRunUpdate
from app.models.search_execution import ManualSearchStartResult
from app.services.ports import ProviderRepository, ProviderRunSubmitter
from app.services.provider_runs import ProviderRunService
from app.services.searches import SearchService

logger = logging.getLogger(__name__)


class ManualSearchService:
    """Create durable provider runs and hand them to bounded execution infrastructure."""

    def __init__(
        self,
        search_service: SearchService,
        provider_repository: ProviderRepository,
        provider_run_service: ProviderRunService,
        provider_run_submitter: ProviderRunSubmitter,
    ) -> None:
        """Create the service with durable state and execution-boundary dependencies."""

        self._search_service = search_service
        self._provider_repository = provider_repository
        self._provider_run_service = provider_run_service
        self._provider_run_submitter = provider_run_submitter

    def start(self, search_id: UUID) -> ManualSearchStartResult:
        """Start enabled configured providers without waiting for their scraping work."""

        search = self._search_service.get(search_id)
        requested_codes = set(search.criteria.provider_codes)
        providers = self._provider_repository.list_enabled(requested_codes or None)
        available_codes = {provider.code for provider in providers}
        skipped_codes = sorted(requested_codes - available_codes)
        if not providers:
            raise NoEnabledProviderError("No enabled provider matches this saved search")

        provider_runs = []
        for provider in providers:
            provider_run = self._provider_run_service.create(
                ProviderRunCreate(provider_id=provider.id, search_id=search_id)
            )
            if not self._provider_run_submitter.submit(provider_run.id):
                provider_run = self._provider_run_service.update(
                    provider_run.id,
                    ProviderRunUpdate(
                        status=ProviderRunStatus.FAILED,
                        error_category="execution_capacity_exhausted",
                        error_summary="The local provider execution queue is full.",
                    ),
                )
            provider_runs.append(provider_run)

        logger.info(
            "manual_search_started",
            extra={
                "search_id": str(search_id),
                "provider_run_count": len(provider_runs),
                "skipped_provider_count": len(skipped_codes),
            },
        )
        return ManualSearchStartResult(
            search_id=search_id,
            provider_runs=provider_runs,
            skipped_provider_codes=skipped_codes,
        )
