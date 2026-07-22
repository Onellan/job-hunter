"""SQLite repository implementation for provider-neutral jobs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func
from sqlmodel import Session, select

from app.database.mappers import to_job_record
from app.database.repositories._helpers import commit_or_raise_conflict
from app.database.tables import JobTable
from app.models.common import PaginatedResult
from app.models.errors import EntityNotFoundError
from app.models.job import JobCandidate, JobRecord


class SqliteJobRepository:
    """Persist and query jobs using SQLModel without exposing SQL to services."""

    def __init__(self, session: Session) -> None:
        """Create a repository backed by one request-scoped session."""

        self._session = session

    def get(self, job_id: UUID) -> JobRecord | None:
        """Return a job by ID when it exists."""

        table = self._session.get(JobTable, job_id)
        return to_job_record(table) if table else None

    def find_by_source_identity(self, source: str, source_job_id: str) -> JobRecord | None:
        """Return a job with a matching stable provider identifier."""

        statement = select(JobTable).where(
            JobTable.source == source,
            JobTable.source_job_id == source_job_id,
        )
        table = self._session.exec(statement).first()
        return to_job_record(table) if table else None

    def find_by_source_url(self, source_url: str) -> JobRecord | None:
        """Return a job with a matching canonical source URL."""

        statement = select(JobTable).where(JobTable.source_url == source_url)
        table = self._session.exec(statement).first()
        return to_job_record(table) if table else None

    def find_by_fingerprint(self, fingerprint: str) -> JobRecord | None:
        """Return a job with a matching deterministic fallback identity."""

        statement = select(JobTable).where(JobTable.fingerprint == fingerprint)
        table = self._session.exec(statement).first()
        return to_job_record(table) if table else None

    def create(self, candidate: JobCandidate, fingerprint: str, now: datetime) -> JobRecord:
        """Persist a newly observed job candidate."""

        table = JobTable(
            source=candidate.source,
            source_job_id=candidate.source_job_id,
            source_url=str(candidate.source_url) if candidate.source_url else None,
            fingerprint=fingerprint,
            title=candidate.title,
            company=candidate.company,
            location=candidate.location,
            workplace_type=candidate.workplace_type.value,
            employment_type=candidate.employment_type.value if candidate.employment_type else None,
            description=candidate.description,
            salary_min=candidate.salary_min,
            salary_max=candidate.salary_max,
            salary_currency=candidate.salary_currency,
            salary_period=candidate.salary_period.value if candidate.salary_period else None,
            published_at=candidate.published_at,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_job_record(table)

    def update(
        self,
        job_id: UUID,
        candidate: JobCandidate,
        fingerprint: str,
        now: datetime,
    ) -> JobRecord:
        """Store the latest candidate fields and observation time for a job."""

        table = self._session.get(JobTable, job_id)
        if table is None:
            raise EntityNotFoundError("Job", job_id)

        table.fingerprint = fingerprint
        table.title = candidate.title
        table.company = candidate.company
        table.location = candidate.location
        table.workplace_type = candidate.workplace_type.value
        table.employment_type = (
            candidate.employment_type.value if candidate.employment_type else None
        )
        table.description = candidate.description
        table.salary_min = candidate.salary_min
        table.salary_max = candidate.salary_max
        table.salary_currency = candidate.salary_currency
        table.salary_period = candidate.salary_period.value if candidate.salary_period else None
        table.published_at = candidate.published_at
        table.last_seen_at = now
        table.updated_at = now
        self._session.add(table)
        commit_or_raise_conflict(self._session)
        self._session.refresh(table)
        return to_job_record(table)

    def list(self, offset: int, limit: int, source: str | None) -> PaginatedResult[JobRecord]:
        """Return latest observed jobs in a bounded deterministic page."""

        statement = select(JobTable)
        count_statement = select(func.count()).select_from(JobTable)
        if source is not None:
            statement = statement.where(JobTable.source == source)
            count_statement = count_statement.where(JobTable.source == source)

        statement = statement.order_by(desc(JobTable.last_seen_at), desc(JobTable.id))
        tables = self._session.exec(statement.offset(offset).limit(limit)).all()
        total = self._session.exec(count_statement).one()
        return PaginatedResult(
            items=[to_job_record(table) for table in tables],
            total=total,
            offset=offset,
            limit=limit,
        )

    def delete(self, job_id: UUID) -> bool:
        """Delete a job without exposing table operations to services."""

        table = self._session.get(JobTable, job_id)
        if table is None:
            return False
        self._session.delete(table)
        commit_or_raise_conflict(self._session)
        return True
