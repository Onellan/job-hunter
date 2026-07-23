"""Contracts for starting a non-blocking manual saved-search execution."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.provider_run import ProviderRunRecord


class ManualSearchStartResult(BaseModel):
    """Durable provider runs accepted for one manually started saved search."""

    search_id: UUID
    provider_runs: list[ProviderRunRecord] = Field(default_factory=list)
    skipped_provider_codes: list[str] = Field(default_factory=list)
