"""Safe notification delivery contracts that never retain recipients or payloads."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationStatus(StrEnum):
    """Durable delivery outcome."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


class NotificationChannel(StrEnum):
    """Supported opt-in delivery integrations."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    SLACK = "slack"
    TEAMS = "teams"


class NotificationDeliveryRecord(BaseModel):
    """Privacy-minimised notification delivery audit event."""

    model_config = ConfigDict(from_attributes=True, frozen=True)
    id: UUID
    channel: NotificationChannel
    event_type: str = Field(max_length=64)
    status: NotificationStatus
    error_category: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class NotificationTestRequest(BaseModel):
    """Validated, non-sensitive request to verify one configured channel."""

    channel: NotificationChannel
