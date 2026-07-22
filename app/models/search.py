"""Saved search contracts independent of provider query syntax."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.job import ProviderCode

SearchText = Annotated[str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)]


class RemotePreference(StrEnum):
    """A user's requested workplace preference for a saved search."""

    ANY = "any"
    ON_SITE = "on_site"
    HYBRID = "hybrid"
    REMOTE = "remote"


class SearchCriteria(BaseModel):
    """Provider-neutral criteria that services later translate per provider."""

    keywords: list[SearchText] = Field(default_factory=list, max_length=20)
    boolean_query: str | None = Field(default=None, max_length=500)
    excluded_keywords: list[SearchText] = Field(default_factory=list, max_length=20)
    locations: list[SearchText] = Field(default_factory=list, max_length=20)
    remote_preference: RemotePreference = RemotePreference.ANY
    minimum_salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    experience_levels: list[SearchText] = Field(default_factory=list, max_length=10)
    posted_within_days: int | None = Field(default=None, ge=1, le=365)
    provider_codes: list[ProviderCode] = Field(default_factory=list, max_length=20)
    included_companies: list[SearchText] = Field(default_factory=list, max_length=20)
    excluded_companies: list[SearchText] = Field(default_factory=list, max_length=20)


class SearchCreate(BaseModel):
    """The name and criteria of a reusable saved search."""

    name: str = Field(min_length=1, max_length=150)
    criteria: SearchCriteria = Field(default_factory=SearchCriteria)
    enabled: bool = True


class SearchUpdate(BaseModel):
    """Mutable saved-search fields."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    criteria: SearchCriteria | None = None
    enabled: bool | None = None


class SearchRecord(SearchCreate):
    """A durable reusable search definition."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
