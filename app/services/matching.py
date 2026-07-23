"""Local resume skill-profile and on-demand job comparison use cases."""

from __future__ import annotations

from uuid import UUID

from app.ai.resume import extract_skills
from app.models.common import utc_now
from app.models.errors import EntityNotFoundError, ResourceValidationError
from app.models.job import JobRecord
from app.models.matching import (
    ComparedJob,
    JobComparisonRequest,
    JobComparisonResult,
    ResumeProfile,
    ResumeUploadRequest,
)
from app.services.ports import ResumeRepository
from app.services.workspace import JobWorkspaceService


class ResumeMatchingService:
    """Manage derived resume skills and compare them against current jobs locally."""

    def __init__(
        self,
        repository: ResumeRepository,
        workspace_service: JobWorkspaceService,
        vocabulary: list[str],
        enabled: bool,
        maximum_characters: int,
    ) -> None:
        """Create the service with persistence, job reads, and bounded extraction settings."""

        self._repository = repository
        self._workspace_service = workspace_service
        self._vocabulary = vocabulary
        self._enabled = enabled
        self._maximum_characters = maximum_characters

    def upload(self, request: ResumeUploadRequest) -> ResumeProfile:
        """Extract and retain only consented skills, immediately discarding source text."""

        self._require_enabled()
        if len(request.content) > self._maximum_characters:
            raise ResourceValidationError("Resume content exceeds the configured size limit")
        return self._repository.replace(
            extract_skills(request.content, self._vocabulary), utc_now()
        )

    def get_profile(self) -> ResumeProfile:
        """Return the current consented profile or report it as absent."""

        self._require_enabled()
        profile = self._repository.get()
        if profile is None:
            raise EntityNotFoundError("Resume profile", UUID(int=0))
        return profile

    def delete_profile(self) -> None:
        """Permanently remove retained derived skills and consent metadata."""

        self._require_enabled()
        if not self._repository.delete():
            raise EntityNotFoundError("Resume profile", UUID(int=0))

    def compare(self, request: JobComparisonRequest) -> JobComparisonResult:
        """Compare two or three jobs against the current profile without persisting results."""

        profile = self.get_profile()
        selected = [self._workspace_service.get(job_id).job for job_id in request.job_ids]
        compared = [self._compare_job(job, profile.skills) for job in selected]
        common = set(compared[0].matched_resume_skills)
        for item in compared[1:]:
            common.intersection_update(item.matched_resume_skills)
        return JobComparisonResult(
            resume_skills=profile.skills,
            common_resume_skills=sorted(common),
            jobs=compared,
        )

    def _compare_job(self, job: JobRecord, resume_skills: list[str]) -> ComparedJob:
        """Determine which profile skills occur in one job's visible title and description."""

        content = " ".join(value for value in (job.title, job.description) if value)
        matched = extract_skills(content, resume_skills)
        return ComparedJob(
            job=job,
            matched_resume_skills=matched,
            missing_resume_skills=[skill for skill in resume_skills if skill not in matched],
        )

    def _require_enabled(self) -> None:
        """Reject calls when the local sensitive-data feature is explicitly disabled."""

        if not self._enabled:
            raise ResourceValidationError("Resume matching is disabled")
