"""Read-model contracts for the lightweight dashboard."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.search import SearchRecord
from app.models.workspace import JobWorkspaceItem


class DashboardSnapshot(BaseModel):
    """Small dashboard summary assembled by one bounded persistence query."""

    model_config = ConfigDict(frozen=True)

    jobs_found_today: int = Field(ge=0)
    last_run_at: datetime | None
    provider_count: int = Field(ge=0)
    enabled_provider_count: int = Field(ge=0)
    error_count_today: int = Field(ge=0)
    recent_searches: list[SearchRecord]
    latest_jobs: list[JobWorkspaceItem]
