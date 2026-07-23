"""Provider-neutral schedule and schedule-run contracts."""

from __future__ import annotations

from datetime import datetime, time
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ScheduleTriggerType(StrEnum):
    """Supported APScheduler trigger representations."""

    DAILY = "daily"
    CRON = "cron"


class ScheduleRunStatus(StrEnum):
    """Durable outcome of dispatching a saved search from a schedule."""

    PENDING = "pending"
    QUEUED = "queued"
    FAILED = "failed"


class ScheduleCreate(BaseModel):
    """Validated definition of one recurring saved-search schedule."""

    name: str = Field(min_length=1, max_length=150)
    search_id: UUID
    trigger_type: ScheduleTriggerType
    daily_time: time | None = None
    cron_expression: str | None = Field(default=None, min_length=9, max_length=100)
    enabled: bool = True
    incremental: bool = True
    retry_limit: int = Field(default=1, ge=0, le=3)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_field_count(cls, value: str | None) -> str | None:
        """Accept APScheduler's portable five-field crontab representation only."""

        if value is not None and len(value.split()) != 5:
            raise ValueError("Cron schedules require a five-field crontab expression")
        return value

    @model_validator(mode="after")
    def validate_trigger(self) -> ScheduleCreate:
        """Require exactly the fields used by the selected trigger type."""

        if self.trigger_type == ScheduleTriggerType.DAILY:
            if self.daily_time is None or self.cron_expression is not None:
                raise ValueError("Daily schedules require daily_time and no cron_expression")
        elif self.cron_expression is None or self.daily_time is not None:
            raise ValueError("Cron schedules require cron_expression and no daily_time")
        return self


class ScheduleUpdate(BaseModel):
    """Mutable fields of a recurring schedule."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    trigger_type: ScheduleTriggerType | None = None
    daily_time: time | None = None
    cron_expression: str | None = Field(default=None, min_length=9, max_length=100)
    enabled: bool | None = None
    incremental: bool | None = None
    retry_limit: int | None = Field(default=None, ge=0, le=3)


class ScheduleRecord(ScheduleCreate):
    """A persisted recurring saved-search schedule."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    last_dispatched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ScheduleRunRecord(BaseModel):
    """A durable record of one scheduled or manual schedule dispatch."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    schedule_id: UUID | None
    search_id: UUID | None
    status: ScheduleRunStatus
    attempt: int
    manual: bool
    provider_run_count: int
    failed_provider_count: int
    error_summary: str | None
    created_at: datetime
    finished_at: datetime | None
