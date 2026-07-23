"""Private, deterministic resume matching and comparison contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.job import JobRecord

ResumeText = Annotated[str, StringConstraints(min_length=20, max_length=200_000)]


class ResumeUploadRequest(BaseModel):
    """Explicit consent and text submitted for local skill extraction only."""

    consent: Literal[True]
    content: ResumeText


class ResumeProfile(BaseModel):
    """Persisted non-sensitive resume-derived skills without source resume text."""

    model_config = ConfigDict(from_attributes=True, frozen=True)
    id: UUID
    skills: list[str] = Field(default_factory=list, max_length=80)
    consented_at: datetime
    consent_version: str
    updated_at: datetime


class JobComparisonRequest(BaseModel):
    """A bounded selection of jobs to compare against the active resume profile."""

    job_ids: list[UUID] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def require_distinct_jobs(self) -> JobComparisonRequest:
        """Reject repeated identifiers that cannot form a meaningful comparison."""

        if len(set(self.job_ids)) != len(self.job_ids):
            raise ValueError("Job comparison requires distinct job IDs")
        return self


class ComparedJob(BaseModel):
    """One job's transparent overlap with the active resume skill profile."""

    job: JobRecord
    matched_resume_skills: list[str] = Field(default_factory=list)
    missing_resume_skills: list[str] = Field(default_factory=list)


class JobComparisonResult(BaseModel):
    """Comparison of selected jobs against an explicitly consented resume profile."""

    resume_skills: list[str] = Field(default_factory=list)
    common_resume_skills: list[str] = Field(default_factory=list)
    jobs: list[ComparedJob] = Field(min_length=2, max_length=3)
