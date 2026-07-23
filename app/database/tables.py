"""SQLModel table mappings for Job-Hunter's first durable schema."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlmodel import Field, SQLModel

from app.models.common import utc_now
from app.models.job import WorkplaceType
from app.models.provider_run import ProviderRunStatus
from app.models.schedule import ScheduleRunStatus


class JobTable(SQLModel, table=True):
    """Durable provider-neutral job data and its deterministic identity."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_jobs_source_source_job_id"),
        UniqueConstraint("source_url", name="uq_jobs_source_url"),
        UniqueConstraint("fingerprint", name="uq_jobs_fingerprint"),
        Index("ix_jobs_source_published_at", "source", "published_at"),
        Index("ix_jobs_workplace_type_published_at", "workplace_type", "published_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source: str = Field(sa_column=Column(String(64), nullable=False, index=True))
    source_job_id: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    source_url: str | None = Field(
        default=None,
        sa_column=Column(String(2_048), nullable=True),
    )
    fingerprint: str = Field(sa_column=Column(String(64), nullable=False))
    title: str = Field(sa_column=Column(String(300), nullable=False))
    company: str | None = Field(default=None, sa_column=Column(String(300), nullable=True))
    location: str | None = Field(default=None, sa_column=Column(String(300), nullable=True))
    workplace_type: str = Field(
        default=WorkplaceType.UNKNOWN.value,
        sa_column=Column(String(20), nullable=False),
    )
    employment_type: str | None = Field(
        default=None,
        sa_column=Column(String(20), nullable=True),
    )
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    salary_min: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(12, 2), nullable=True),
    )
    salary_max: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(12, 2), nullable=True),
    )
    salary_currency: str | None = Field(default=None, sa_column=Column(String(3), nullable=True))
    salary_period: str | None = Field(
        default=None,
        sa_column=Column(String(20), nullable=True),
    )
    published_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
    )
    first_seen_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    last_seen_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class JobWorkflowTable(SQLModel, table=True):
    """Optional user-managed state that is deleted with its durable job."""

    __tablename__ = "job_workflows"
    __table_args__ = (
        Index("ix_job_workflows_bookmarked_updated_at", "is_bookmarked", "updated_at"),
        Index("ix_job_workflows_applied_updated_at", "is_applied", "updated_at"),
    )

    job_id: UUID = Field(
        sa_column=Column(
            Uuid(),
            ForeignKey("jobs.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        )
    )
    is_bookmarked: bool = Field(default=False, nullable=False, index=True)
    is_applied: bool = Field(default=False, nullable=False, index=True)
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ExportEventTable(SQLModel, table=True):
    """Privacy-minimised audit record for a user-initiated data export."""

    __tablename__ = "export_events"
    __table_args__ = (Index("ix_export_events_created_at", "created_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    format: str = Field(sa_column=Column(String(20), nullable=False, index=True))
    resource: str = Field(sa_column=Column(String(32), nullable=False))
    selected_job_count: int | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class UserTable(SQLModel, table=True):
    """One local authenticated user with a salted password verifier only."""

    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    password_hash: str = Field(sa_column=Column(String(255), nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class SessionTable(SQLModel, table=True):
    """Durable hashed session and CSRF tokens with an explicit expiry timestamp."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_expires_at", "expires_at"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    )
    token_digest: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    csrf_digest: str = Field(sa_column=Column(String(64), nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class NotificationDeliveryTable(SQLModel, table=True):
    """Safe notification history without recipient, payload, or secret data."""
    __tablename__ = "notification_deliveries"
    __table_args__ = (Index("ix_notification_deliveries_created_at", "created_at"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    channel: str = Field(sa_column=Column(String(32), nullable=False, index=True))
    event_type: str = Field(sa_column=Column(String(64), nullable=False))
    status: str = Field(sa_column=Column(String(20), nullable=False))
    error_category: str | None = Field(default=None, sa_column=Column(String(64), nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    finished_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class ResumeProfileTable(SQLModel, table=True):
    """A single-user's consented, resume-derived skills without raw resume content."""

    __tablename__ = "resume_profiles"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    consented_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    consent_version: str = Field(
        default="resume_skills_v1",
        sa_column=Column(String(32), nullable=False),
    )
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class ProviderTable(SQLModel, table=True):
    """Durable provider enablement and non-secret configuration."""

    __tablename__ = "providers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    display_name: str = Field(sa_column=Column(String(100), nullable=False))
    enabled: bool = Field(default=True, nullable=False, index=True)
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class SearchTable(SQLModel, table=True):
    """Durable provider-neutral search definitions."""

    __tablename__ = "searches"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(sa_column=Column(String(150), nullable=False, index=True))
    criteria: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    enabled: bool = Field(default=True, nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ScheduleTable(SQLModel, table=True):
    """A durable recurring execution definition for one saved search."""

    __tablename__ = "schedules"
    __table_args__ = (
        Index("ix_schedules_enabled_trigger_type", "enabled", "trigger_type"),
        Index("ix_schedules_search_id", "search_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(sa_column=Column(String(150), nullable=False))
    search_id: UUID = Field(
        sa_column=Column(Uuid(), ForeignKey("searches.id", ondelete="RESTRICT"), nullable=False)
    )
    trigger_type: str = Field(sa_column=Column(String(10), nullable=False))
    daily_time: time | None = Field(default=None, sa_column=Column(Time, nullable=True))
    cron_expression: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    enabled: bool = Field(default=True, nullable=False, index=True)
    incremental: bool = Field(default=True, nullable=False)
    retry_limit: int = Field(default=1, nullable=False)
    last_dispatched_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )


class ScheduleRunTable(SQLModel, table=True):
    """Small durable history row for each schedule dispatch attempt."""

    __tablename__ = "schedule_runs"
    __table_args__ = (Index("ix_schedule_runs_schedule_created_at", "schedule_id", "created_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    schedule_id: UUID | None = Field(
        default=None,
        sa_column=Column(Uuid(), ForeignKey("schedules.id", ondelete="SET NULL"), nullable=True),
    )
    search_id: UUID | None = Field(
        default=None,
        sa_column=Column(Uuid(), ForeignKey("searches.id", ondelete="SET NULL"), nullable=True),
    )
    status: str = Field(
        default=ScheduleRunStatus.PENDING.value, sa_column=Column(String(20), nullable=False)
    )
    attempt: int = Field(default=0, nullable=False)
    manual: bool = Field(default=False, nullable=False)
    provider_run_count: int = Field(default=0, nullable=False)
    failed_provider_count: int = Field(default=0, nullable=False)
    error_summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    finished_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class ProviderRunTable(SQLModel, table=True):
    """Durable execution state for one provider against an optional search."""

    __tablename__ = "provider_runs"
    __table_args__ = (
        Index("ix_provider_runs_provider_created_at", "provider_id", "created_at"),
        Index("ix_provider_runs_search_created_at", "search_id", "created_at"),
        Index("ix_provider_runs_status_created_at", "status", "created_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    provider_id: UUID = Field(
        sa_column=Column(
            Uuid(),
            ForeignKey("providers.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    search_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            Uuid(),
            ForeignKey("searches.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    status: str = Field(
        default=ProviderRunStatus.PENDING.value,
        sa_column=Column(String(20), nullable=False),
    )
    result_count: int = Field(default=0, ge=0, nullable=False)
    error_category: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    error_summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
