"""Bounded local execution adapter for durable provider runs."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from threading import BoundedSemaphore, Lock
from uuid import UUID

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.core.config import ProviderExecutionSettings
from app.database.repositories import (
    SqliteJobRepository,
    SqliteProviderRepository,
    SqliteProviderRunRepository,
    SqliteSearchRepository,
)
from app.models.errors import EntityNotFoundError
from app.models.provider_run import ProviderRunStatus, ProviderRunUpdate
from app.providers.errors import ProviderError
from app.providers.registry import ProviderRegistry
from app.services.jobs import JobService
from app.services.provider_runs import ProviderRunService
from app.services.providers import ProviderService
from app.services.searches import SearchService

logger = logging.getLogger(__name__)


class BoundedProviderExecutor:
    """Run provider work in a fixed local thread pool with a bounded queue."""

    def __init__(
        self,
        engine: Engine,
        registry: ProviderRegistry,
        settings: ProviderExecutionSettings,
    ) -> None:
        """Create a process-scoped executor suitable for low-memory deployments."""

        self._engine = engine
        self._registry = registry
        self._executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_runs,
            thread_name_prefix="job-hunter-provider",
        )
        capacity = settings.max_concurrent_runs + settings.max_queued_runs
        self._capacity = BoundedSemaphore(capacity)
        self._futures: dict[Future[None], UUID] = {}
        self._futures_lock = Lock()

    def submit(self, run_id: UUID) -> bool:
        """Schedule a durable run immediately when bounded capacity is available."""

        if not self._capacity.acquire(blocking=False):
            logger.warning("provider_run_rejected", extra={"provider_run_id": str(run_id)})
            return False
        try:
            future = self._executor.submit(self._execute_safely, run_id)
        except RuntimeError:
            self._capacity.release()
            logger.warning("provider_run_rejected", extra={"provider_run_id": str(run_id)})
            return False

        with self._futures_lock:
            self._futures[future] = run_id
        future.add_done_callback(self._release_capacity)
        return True

    def shutdown(self) -> None:
        """Cancel queued work during application shutdown without blocking exit."""

        self._executor.shutdown(wait=False, cancel_futures=True)

    def _execute_safely(self, run_id: UUID) -> None:
        """Ensure an unexpected execution failure is recorded instead of escaping a worker."""

        try:
            self._execute(run_id)
        except Exception:
            # This is the outer worker boundary; do not include provider payloads in logs.
            logger.error("provider_run_crashed", extra={"provider_run_id": str(run_id)})
            self._mark_failed_if_possible(
                run_id, "execution_crashed", "The provider run ended unexpectedly."
            )

    def _execute(self, run_id: UUID) -> None:
        """Run one provider and persist successful jobs or an isolated failure outcome."""

        with Session(self._engine) as session:
            provider_repository = SqliteProviderRepository(session)
            search_repository = SqliteSearchRepository(session)
            run_repository = SqliteProviderRunRepository(session)
            run_service = ProviderRunService(provider_repository, search_repository, run_repository)
            run = run_service.get(run_id)
            if run.status != ProviderRunStatus.PENDING:
                return

            try:
                provider_record = ProviderService(provider_repository).get(run.provider_id)
                if run.search_id is None:
                    raise ProviderError("Provider runs require a saved search")
                search = SearchService(search_repository).get(run.search_id)
                run_service.update(run_id, ProviderRunUpdate(status=ProviderRunStatus.RUNNING))
                provider = self._registry.create(provider_record.code)
                job_service = JobService(SqliteJobRepository(session))
                result_count = 0
                for candidate in provider.search(search.criteria, provider_record.configuration):
                    job_service.upsert(candidate)
                    result_count += 1
                run_service.update(
                    run_id,
                    ProviderRunUpdate(
                        status=ProviderRunStatus.SUCCEEDED,
                        result_count=result_count,
                    ),
                )
                logger.info(
                    "provider_run_completed",
                    extra={
                        "provider_run_id": str(run_id),
                        "provider_code": provider_record.code,
                        "result_count": result_count,
                    },
                )
            except ProviderError as exception:
                self._mark_failed(
                    run_service,
                    run_id,
                    exception.category,
                    exception.summary,
                )
            except EntityNotFoundError:
                self._mark_failed(
                    run_service,
                    run_id,
                    "configuration_missing",
                    "The provider or saved search no longer exists.",
                )

    def _release_capacity(self, future: Future[None]) -> None:
        """Release the bounded slot and mark canceled queued runs as canceled."""

        with self._futures_lock:
            run_id = self._futures.pop(future, None)
        self._capacity.release()
        if future.cancelled() and run_id is not None:
            self._mark_failed_if_possible(
                run_id,
                "application_shutdown",
                "The provider run was canceled while the application shut down.",
                status=ProviderRunStatus.CANCELLED,
            )

    def _mark_failed(
        self,
        run_service: ProviderRunService,
        run_id: UUID,
        category: str,
        summary: str,
    ) -> None:
        """Persist a safe failure result for one already-running provider run."""

        run_service.update(
            run_id,
            ProviderRunUpdate(
                status=ProviderRunStatus.FAILED,
                error_category=category,
                error_summary=summary,
            ),
        )
        logger.warning(
            "provider_run_failed",
            extra={"provider_run_id": str(run_id), "error_category": category},
        )

    def _mark_failed_if_possible(
        self,
        run_id: UUID,
        category: str,
        summary: str,
        status: ProviderRunStatus = ProviderRunStatus.FAILED,
    ) -> None:
        """Record an outer-worker failure when the database remains available."""

        try:
            with Session(self._engine) as session:
                provider_repository = SqliteProviderRepository(session)
                search_repository = SqliteSearchRepository(session)
                run_repository = SqliteProviderRunRepository(session)
                run_service = ProviderRunService(
                    provider_repository, search_repository, run_repository
                )
                run_service.update(
                    run_id,
                    ProviderRunUpdate(
                        status=status,
                        error_category=category,
                        error_summary=summary,
                    ),
                )
        except Exception:
            logger.error("provider_run_failure_unrecorded", extra={"provider_run_id": str(run_id)})
