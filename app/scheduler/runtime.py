"""Low-memory APScheduler adapter that dispatches saved searches through services."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from app.core.config import SchedulerSettings
from app.database.repositories import (
    SqliteProviderRepository,
    SqliteProviderRunRepository,
    SqliteScheduleRepository,
    SqliteSearchRepository,
)
from app.models.schedule import ScheduleRecord, ScheduleRunStatus, ScheduleTriggerType
from app.providers.execution import BoundedProviderExecutor
from app.services.manual_searches import ManualSearchService
from app.services.provider_runs import ProviderRunService
from app.services.schedules import ScheduleService
from app.services.searches import SearchService

logger = logging.getLogger(__name__)


class SchedulerRuntime:
    """Register persisted schedules and dispatch them without holding database transactions."""

    def __init__(
        self,
        engine: Engine,
        settings: SchedulerSettings,
        provider_executor: BoundedProviderExecutor,
    ) -> None:
        """Create one process-local scheduler with a single lightweight dispatcher thread."""

        self._engine = engine
        self._settings = settings
        self._provider_executor = provider_executor
        self._scheduler = BackgroundScheduler(
            timezone=UTC,
            executors={"default": ThreadPoolExecutor(max_workers=1)},
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
            daemon=True,
        )

    def start(self) -> None:
        """Start APScheduler and register enabled persisted schedules once per process."""

        if not self._settings.enabled:
            logger.info("scheduler_disabled")
            return
        self._scheduler.start()
        try:
            schedules = self._list_schedules()
        except OperationalError:
            # Health checks can start before an operator applies the required migration.
            logger.warning("scheduler_schema_unavailable")
            return
        for schedule in schedules:
            self.sync(schedule)
        logger.info("scheduler_started")

    def shutdown(self) -> None:
        """Stop dispatching new work without waiting for provider worker completion."""

        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

    def sync(self, schedule: ScheduleRecord) -> None:
        """Add, replace, or remove the in-memory trigger for one durable schedule."""

        if not self._settings.enabled:
            return
        job_id = self._job_id(schedule.id)
        if not schedule.enabled:
            self._scheduler.remove_job(job_id) if self._scheduler.get_job(job_id) else None
            return
        self._scheduler.add_job(
            self.dispatch,
            trigger=self._trigger_for(schedule),
            args=[schedule.id, 0, False],
            id=job_id,
            replace_existing=True,
        )

    def remove(self, schedule_id: UUID) -> None:
        """Remove an in-memory trigger after its durable schedule is deleted."""

        job_id = self._job_id(schedule_id)
        if self._scheduler.running and self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

    def run_now(self, schedule_id: UUID) -> None:
        """Queue an immediate manual dispatch without blocking the calling request."""

        if not self._settings.enabled:
            raise RuntimeError("Scheduling is disabled by configuration")
        self._scheduler.add_job(
            self.dispatch,
            trigger="date",
            run_date=datetime.now(UTC),
            args=[schedule_id, 0, True],
        )

    def dispatch(self, schedule_id: UUID, attempt: int = 0, manual: bool = False) -> None:
        """Create history, queue provider runs, and bound retryable dispatch failures."""

        with Session(self._engine) as session:
            schedules = ScheduleService(
                SqliteScheduleRepository(session), SqliteSearchRepository(session)
            )
            schedule = schedules.get(schedule_id)
            run = schedules.start_run(schedule_id, attempt, manual)
            manual_search = self._manual_search_service(session)
            try:
                result = manual_search.start(schedule.search_id)
            except (
                Exception
            ) as exception:  # A scheduler boundary must retain dispatch failure history.
                logger.exception(
                    "scheduled_search_dispatch_failed", extra={"schedule_id": str(schedule_id)}
                )
                schedules.finish_run(
                    run.id, ScheduleRunStatus.FAILED, 0, 0, type(exception).__name__
                )
                self._retry(schedule, attempt)
                return

            failed_count = sum(
                provider_run.status.value == "failed" for provider_run in result.provider_runs
            )
            schedules.finish_run(
                run.id,
                ScheduleRunStatus.QUEUED,
                len(result.provider_runs),
                failed_count,
                None,
            )
            schedules.mark_dispatched(schedule_id)
            if failed_count == len(result.provider_runs):
                self._retry(schedule, attempt)
            logger.info(
                "scheduled_search_queued",
                extra={
                    "schedule_id": str(schedule_id),
                    "provider_run_count": len(result.provider_runs),
                },
            )

    def _retry(self, schedule: ScheduleRecord, attempt: int) -> None:
        """Schedule one capped delayed retry for a dispatch that queued no provider work."""

        if attempt >= schedule.retry_limit:
            return
        self._scheduler.add_job(
            self.dispatch,
            trigger="date",
            run_date=datetime.now(UTC) + timedelta(seconds=self._settings.retry_delay_seconds),
            args=[schedule.id, attempt + 1, False],
        )

    def _list_schedules(self) -> list[ScheduleRecord]:
        """Read all modest local schedule definitions during application startup."""

        with Session(self._engine) as session:
            return (
                ScheduleService(SqliteScheduleRepository(session), SqliteSearchRepository(session))
                .list(0, self._settings.max_registered_schedules)
                .items
            )

    def _manual_search_service(self, session: Session) -> ManualSearchService:
        """Compose the existing provider execution use case with a short-lived session."""

        providers = SqliteProviderRepository(session)
        searches = SqliteSearchRepository(session)
        return ManualSearchService(
            search_service=SearchService(searches),
            provider_repository=providers,
            provider_run_service=ProviderRunService(
                providers, searches, SqliteProviderRunRepository(session)
            ),
            provider_run_submitter=self._provider_executor,
        )

    @staticmethod
    def _job_id(schedule_id: UUID) -> str:
        """Return a deterministic APScheduler job identifier."""

        return f"schedule:{schedule_id}"

    @staticmethod
    def _trigger_for(schedule: ScheduleRecord) -> CronTrigger:
        """Translate a validated durable trigger into an APScheduler cron trigger."""

        if schedule.trigger_type == ScheduleTriggerType.DAILY:
            assert schedule.daily_time is not None
            return CronTrigger(
                hour=schedule.daily_time.hour, minute=schedule.daily_time.minute, timezone=UTC
            )
        assert schedule.cron_expression is not None
        return CronTrigger.from_crontab(schedule.cron_expression, timezone=UTC)
