"""Deterministic, explainable job-scoring contracts and user preferences."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.models.job import JobRecord
from app.models.search import RemotePreference

ScoringText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=100, strip_whitespace=True),
]


class ScoringProfile(BaseModel):
    """Local user preferences used by the deterministic scoring engine."""

    target_roles: list[ScoringText] = Field(default_factory=list, max_length=20)
    skills: list[ScoringText] = Field(default_factory=list, max_length=50)
    minimum_salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    remote_preference: RemotePreference = RemotePreference.ANY
    minimum_experience_years: int | None = Field(default=None, ge=0, le=50)
    leadership: bool = False
    project_management: bool = False
    business_analysis: bool = False
    agile: bool = False


class JobScore(BaseModel):
    """An explainable score for one job against the configured local profile."""

    score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class JobScoreResult(BaseModel):
    """A durable job paired with its current computed deterministic score."""

    job: JobRecord
    score: JobScore
