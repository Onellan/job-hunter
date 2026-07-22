"""Shared provider-neutral model primitives."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class PaginatedResult[ItemType](BaseModel):
    """A bounded page of results and the information needed to request another."""

    model_config = ConfigDict(frozen=True)

    items: list[ItemType]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
