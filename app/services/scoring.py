"""Application use case that scores existing workspace jobs without persistence changes."""

from __future__ import annotations

from uuid import UUID

from app.ai.scoring import DeterministicJobScorer
from app.models.scoring import JobScoreResult, ScoringProfile
from app.services.workspace import JobWorkspaceService


class JobScoringService:
    """Return a current deterministic score for one persisted workspace job."""

    def __init__(self, workspace_service: JobWorkspaceService, profile: ScoringProfile) -> None:
        """Create the scoring use case from a workspace reader and local preferences."""

        self._workspace_service = workspace_service
        self._profile = profile
        self._scorer = DeterministicJobScorer()

    def score_job(self, job_id: UUID) -> JobScoreResult:
        """Load one job and calculate its non-persistent, explainable score."""

        item = self._workspace_service.get(job_id)
        return JobScoreResult(job=item.job, score=self._scorer.score(item.job, self._profile))
