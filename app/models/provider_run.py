"""Durable provider-run contracts and state transition rules."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.errors import ProviderRunTransitionError


class ProviderRunStatus(StrEnum):
    """The lifecycle states of a single provider execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProviderRunCreate(BaseModel):
    """A request to create a pending execution for a registered provider."""

    provider_id: UUID
    search_id: UUID | None = None


class ProviderRunUpdate(BaseModel):
    """Progress and terminal outcome reported for a provider execution."""

    status: ProviderRunStatus | None = None
    result_count: int | None = Field(default=None, ge=0)
    error_category: str | None = Field(default=None, max_length=100)
    error_summary: str | None = Field(default=None, max_length=1_000)


class ProviderRunRecord(ProviderRunCreate):
    """A durable provider run with safe outcome metadata."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    status: ProviderRunStatus
    result_count: int
    error_category: str | None
    error_summary: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


def validate_provider_run_transition(
    current: ProviderRunStatus,
    requested: ProviderRunStatus,
) -> None:
    """Raise when a provider run is asked to take an invalid next step."""

    allowed_transitions: dict[ProviderRunStatus, set[ProviderRunStatus]] = {
        ProviderRunStatus.PENDING: {
            ProviderRunStatus.RUNNING,
            ProviderRunStatus.FAILED,
            ProviderRunStatus.CANCELLED,
        },
        ProviderRunStatus.RUNNING: {
            ProviderRunStatus.SUCCEEDED,
            ProviderRunStatus.FAILED,
            ProviderRunStatus.CANCELLED,
        },
        ProviderRunStatus.SUCCEEDED: set(),
        ProviderRunStatus.FAILED: set(),
        ProviderRunStatus.CANCELLED: set(),
    }
    if requested != current and requested not in allowed_transitions[current]:
        message = f"Cannot transition provider run from {current} to {requested}"
        raise ProviderRunTransitionError(message)
