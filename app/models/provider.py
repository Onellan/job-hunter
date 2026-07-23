"""Provider configuration contracts independent of provider implementations."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, field_validator

ProviderName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_-]{1,63}$", strip_whitespace=True),
]
ProviderAvailabilityReason = Literal["dependency_unavailable", "browser_unavailable"]


class ProviderDefinition(BaseModel):
    """Provider-owned defaults and safe local runtime availability."""

    code: ProviderName
    display_name: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    configuration: dict[str, JsonValue] = Field(default_factory=dict)
    availability_reason: ProviderAvailabilityReason | None = None
    bootstrap: bool = False

    @field_validator("configuration")
    @classmethod
    def reject_secret_like_configuration(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Keep discovery-owned defaults subject to the normal secret policy."""

        if _contains_sensitive_key(value):
            raise ValueError("Provider configuration must not contain credentials")
        return value

    def as_create(self) -> ProviderCreate:
        """Return the durable fields required when the provider row is missing."""

        return ProviderCreate(
            code=self.code,
            display_name=self.display_name,
            enabled=self.enabled,
            configuration=self.configuration,
        )


class ProviderCreate(BaseModel):
    """Configuration needed to register a provider implementation by name."""

    code: ProviderName
    display_name: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    configuration: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("configuration")
    @classmethod
    def reject_secret_like_configuration(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        """Prevent accidental persistence of credentials in provider configuration."""

        if _contains_sensitive_key(value):
            raise ValueError("Provider configuration must not contain credentials")
        return value


class ProviderUpdate(BaseModel):
    """Mutable provider configuration fields."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None
    configuration: dict[str, JsonValue] | None = None

    @field_validator("configuration")
    @classmethod
    def reject_secret_like_configuration(
        cls, value: dict[str, JsonValue] | None
    ) -> dict[str, JsonValue] | None:
        """Apply the same non-secret policy to partial provider updates."""

        if value is not None and _contains_sensitive_key(value):
            raise ValueError("Provider configuration must not contain credentials")
        return value


class ProviderRecord(ProviderCreate):
    """A durable provider registration."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    availability_reason: ProviderAvailabilityReason | None = None


def _contains_sensitive_key(value: object) -> bool:
    """Detect common credential keys recursively without inspecting values."""

    sensitive_parts = (
        "password",
        "token",
        "secret",
        "apikey",
        "authorization",
        "cookie",
        "credential",
        "privatekey",
        "bearer",
        "session",
        "headers",
    )
    if isinstance(value, dict):
        return any(
            any(part in _normalise_key(str(key)) for part in sensitive_parts)
            or _contains_sensitive_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_key(child) for child in value)
    return False


def _normalise_key(value: str) -> str:
    """Normalise casing and separators before checking a configuration key."""

    return "".join(character for character in value.casefold() if character.isalnum())
