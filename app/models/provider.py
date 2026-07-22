"""Provider configuration contracts independent of provider implementations."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

ProviderName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_-]{1,63}$", strip_whitespace=True),
]


class ProviderCreate(BaseModel):
    """Configuration needed to register a provider implementation by name."""

    code: ProviderName
    display_name: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    configuration: dict[str, JsonValue] = Field(default_factory=dict)


class ProviderUpdate(BaseModel):
    """Mutable provider configuration fields."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None
    configuration: dict[str, JsonValue] | None = None


class ProviderRecord(ProviderCreate):
    """A durable provider registration."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
