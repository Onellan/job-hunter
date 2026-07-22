"""Provider-neutral job contracts and deterministic identity helpers."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

from app.models.common import utc_now

ProviderCode = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_-]{1,63}$", strip_whitespace=True),
]


class WorkplaceType(StrEnum):
    """Where an employer expects the work to be performed."""

    UNKNOWN = "unknown"
    ON_SITE = "on_site"
    HYBRID = "hybrid"
    REMOTE = "remote"


class EmploymentType(StrEnum):
    """A normalised employment arrangement when a provider reports one."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    OTHER = "other"


class SalaryPeriod(StrEnum):
    """The interval represented by a normalised salary amount."""

    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class JobCandidate(BaseModel):
    """The provider-neutral job data accepted from an acquisition adapter."""

    source: ProviderCode
    source_job_id: str | None = Field(default=None, max_length=255)
    source_url: HttpUrl | None = None
    title: str = Field(min_length=1, max_length=300)
    company: str | None = Field(default=None, max_length=300)
    location: str | None = Field(default=None, max_length=300)
    workplace_type: WorkplaceType = WorkplaceType.UNKNOWN
    employment_type: EmploymentType | None = None
    description: str | None = Field(default=None, max_length=100_000)
    salary_min: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    salary_max: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    salary_period: SalaryPeriod | None = None
    published_at: datetime | None = None

    @model_validator(mode="after")
    def validate_salary_range(self) -> JobCandidate:
        """Reject incomplete or inverted normalised salary ranges."""

        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("salary_min cannot be greater than salary_max")
        if (self.salary_min is not None or self.salary_max is not None) and (
            self.salary_currency is None or self.salary_period is None
        ):
            raise ValueError("salary amounts require a currency and period")
        return self


class JobUpdate(BaseModel):
    """User-editable job fields that do not alter durable source identity."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    company: str | None = Field(default=None, max_length=300)
    location: str | None = Field(default=None, max_length=300)
    workplace_type: WorkplaceType | None = None
    employment_type: EmploymentType | None = None
    description: str | None = Field(default=None, max_length=100_000)
    salary_min: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    salary_max: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    salary_period: SalaryPeriod | None = None
    published_at: datetime | None = None


class JobRecord(JobCandidate):
    """A durable job and its safe discovery metadata."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class JobUpsertResult(BaseModel):
    """The result of ingesting a provider-neutral job candidate."""

    job: JobRecord
    created: bool


def calculate_job_fingerprint(candidate: JobCandidate) -> str:
    """Create a deterministic cross-provider fallback identity for a job.

    The fingerprint deliberately excludes source-specific identifiers and long
    descriptions. It is used only after a stable source identifier and canonical
    URL cannot establish identity.
    """

    published_date = candidate.published_at.date().isoformat() if candidate.published_at else ""
    identity_values = (candidate.title, candidate.company, candidate.location, published_date)
    normalized_values = (_normalize_identity_value(value) for value in identity_values)
    payload = "\x1f".join(normalized_values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_identity_value(value: str | None) -> str:
    """Normalise a durable job field for stable matching."""

    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"\s+", " ", normalized)


def candidate_fields(record: JobRecord) -> dict[str, object]:
    """Extract candidate fields from a durable record for safe patch merging."""

    return record.model_dump(include=set(JobCandidate.model_fields), mode="python")


def observed_at() -> datetime:
    """Return the timestamp used when a provider re-observes a job."""

    return utc_now()
