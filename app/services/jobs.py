"""Application service for durable provider-neutral job records."""

from __future__ import annotations

from uuid import UUID

from app.models.common import PaginatedResult
from app.models.errors import EntityNotFoundError, ResourceConflictError
from app.models.job import (
    JobCandidate,
    JobRecord,
    JobUpdate,
    JobUpsertResult,
    calculate_job_fingerprint,
    candidate_fields,
    observed_at,
)
from app.services.ports import JobRepository


class JobService:
    """Coordinate job identity, deduplication, and CRUD without SQL knowledge."""

    def __init__(self, repository: JobRepository) -> None:
        """Create the service with a provider-neutral job repository."""

        self._repository = repository

    def upsert(self, candidate: JobCandidate) -> JobUpsertResult:
        """Create or refresh a job according to the durable identity hierarchy."""

        fingerprint = calculate_job_fingerprint(candidate)
        existing = self._find_existing(candidate, fingerprint)
        timestamp = observed_at()
        if existing is not None:
            job = self._repository.update(existing.id, candidate, fingerprint, timestamp)
            return JobUpsertResult(job=job, created=False)

        try:
            job = self._repository.create(candidate, fingerprint, timestamp)
        except ResourceConflictError:
            existing = self._find_existing(candidate, fingerprint)
            if existing is None:
                raise
            job = self._repository.update(existing.id, candidate, fingerprint, timestamp)
            return JobUpsertResult(job=job, created=False)
        return JobUpsertResult(job=job, created=True)

    def get(self, job_id: UUID) -> JobRecord:
        """Return a durable job or raise a domain-specific missing-resource error."""

        job = self._repository.get(job_id)
        if job is None:
            raise EntityNotFoundError("Job", job_id)
        return job

    def list(self, offset: int, limit: int, source: str | None) -> PaginatedResult[JobRecord]:
        """Return a bounded latest-observation-first page of jobs."""

        return self._repository.list(offset, limit, source)

    def update(self, job_id: UUID, changes: JobUpdate) -> JobRecord:
        """Apply source-identity-safe changes while preserving deduplication invariants."""

        existing = self.get(job_id)
        candidate_payload = candidate_fields(existing)
        candidate_payload.update(changes.model_dump(exclude_unset=True, mode="python"))
        candidate = JobCandidate.model_validate(candidate_payload)
        fingerprint = calculate_job_fingerprint(candidate)
        same_fingerprint = self._repository.find_by_fingerprint(fingerprint)
        if same_fingerprint is not None and same_fingerprint.id != job_id:
            raise ResourceConflictError("The updated job would duplicate an existing job")
        return self._repository.update(job_id, candidate, fingerprint, observed_at())

    def delete(self, job_id: UUID) -> None:
        """Delete a job or raise a missing-resource error."""

        if not self._repository.delete(job_id):
            raise EntityNotFoundError("Job", job_id)

    def _find_existing(self, candidate: JobCandidate, fingerprint: str) -> JobRecord | None:
        """Resolve an existing job using stable ID, URL, then fallback fingerprint."""

        if candidate.source_job_id:
            existing = self._repository.find_by_source_identity(
                candidate.source,
                candidate.source_job_id,
            )
            if existing is not None:
                return existing
        if candidate.source_url:
            existing = self._repository.find_by_source_url(str(candidate.source_url))
            if existing is not None:
                return existing
        return self._repository.find_by_fingerprint(fingerprint)
