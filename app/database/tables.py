"""SQLModel table mappings for Job-Hunter's first durable schema."""

from __future__ import annotations

from datetime import datetime
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
    UniqueConstraint,
    Uuid,
)
from sqlmodel import Field, SQLModel

from app.models.common import utc_now
from app.models.job import WorkplaceType
from app.models.provider_run import ProviderRunStatus


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
