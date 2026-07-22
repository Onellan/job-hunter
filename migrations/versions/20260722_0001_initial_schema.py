"""Create Job-Hunter's initial durable domain schema.

Revision ID: 20260722_0001
Revises:
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial provider, search, job, and run tables with indexes."""

    op.create_table(
        "providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_providers_code"),
    )
    op.create_index("ix_providers_enabled", "providers", ["enabled"], unique=False)

    op.create_table(
        "searches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_searches_name", "searches", ["name"], unique=False)
    op.create_index("ix_searches_enabled", "searches", ["enabled"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_job_id", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("company", sa.String(length=300), nullable=True),
        sa.Column("location", sa.String(length=300), nullable=True),
        sa.Column("workplace_type", sa.String(length=20), nullable=False),
        sa.Column("employment_type", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_currency", sa.String(length=3), nullable=True),
        sa.Column("salary_period", sa.String(length=20), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_job_id", name="uq_jobs_source_source_job_id"),
        sa.UniqueConstraint("source_url", name="uq_jobs_source_url"),
        sa.UniqueConstraint("fingerprint", name="uq_jobs_fingerprint"),
    )
    op.create_index("ix_jobs_source", "jobs", ["source"], unique=False)
    op.create_index("ix_jobs_published_at", "jobs", ["published_at"], unique=False)
    op.create_index("ix_jobs_first_seen_at", "jobs", ["first_seen_at"], unique=False)
    op.create_index("ix_jobs_last_seen_at", "jobs", ["last_seen_at"], unique=False)
    op.create_index("ix_jobs_source_published_at", "jobs", ["source", "published_at"], unique=False)
    op.create_index(
        "ix_jobs_workplace_type_published_at",
        "jobs",
        ["workplace_type", "published_at"],
        unique=False,
    )

    op.create_table(
        "provider_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("search_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["search_id"], ["searches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_runs_provider_id", "provider_runs", ["provider_id"], unique=False)
    op.create_index("ix_provider_runs_search_id", "provider_runs", ["search_id"], unique=False)
    op.create_index(
        "ix_provider_runs_provider_created_at",
        "provider_runs",
        ["provider_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_provider_runs_search_created_at",
        "provider_runs",
        ["search_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_provider_runs_status_created_at",
        "provider_runs",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the initial tables in dependency order."""

    op.drop_table("provider_runs")
    op.drop_table("jobs")
    op.drop_table("searches")
    op.drop_table("providers")
