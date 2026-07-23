"""Deterministic tests for explainable local job scoring."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.ai.scoring import DeterministicJobScorer
from app.models.job import JobRecord, WorkplaceType
from app.models.scoring import ScoringProfile
from app.models.search import RemotePreference


def test_deterministic_scorer_reports_weighted_matches_gaps_and_confidence() -> None:
    """All requested dimensions contribute predictable, explainable local points."""

    score = DeterministicJobScorer().score(
        _job(),
        ScoringProfile(
            target_roles=["data engineer"],
            skills=["python", "sql", "azure"],
            minimum_salary=Decimal("90000"),
            remote_preference=RemotePreference.REMOTE,
            minimum_experience_years=5,
            leadership=True,
            project_management=True,
            business_analysis=True,
            agile=True,
        ),
    )

    assert score.score == 92
    assert score.confidence == 100
    assert score.matched_skills == ["python", "sql"]
    assert score.missing_skills == ["azure"]
    assert "Matches target role: data engineer." in score.reasons
    assert "Mentions agile delivery." in score.reasons


def test_deterministic_scorer_declines_to_score_without_preferences() -> None:
    """An empty profile produces an honest configuration prompt rather than fake precision."""

    score = DeterministicJobScorer().score(_job(), ScoringProfile())

    assert score.score == 0
    assert score.confidence == 0
    assert score.reasons == ["Configure scoring preferences to calculate a match score."]


def _job() -> JobRecord:
    """Return a standard job fixture containing all supported scoring signals."""

    timestamp = datetime(2026, 7, 22, tzinfo=UTC)
    return JobRecord(
        id=uuid4(),
        source="fixture",
        source_job_id="scoring-1",
        source_url="https://jobs.example.test/scoring-1",
        title="Senior Data Engineer",
        company="Example Ltd",
        location="Cape Town",
        workplace_type=WorkplaceType.REMOTE,
        description=(
            "Lead agile data platform delivery, mentor engineers, gather business analysis "
            "requirements, and manage projects. Requires 3 years of experience in Python and SQL."
        ),
        salary_min=Decimal("95000"),
        salary_max=Decimal("120000"),
        salary_currency="ZAR",
        salary_period="year",
        first_seen_at=timestamp,
        last_seen_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )
