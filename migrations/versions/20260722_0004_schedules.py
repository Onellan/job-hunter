"""Add persisted recurring schedules and dispatch history.

Revision ID: 20260722_0004
Revises: 20260722_0003
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0004"
down_revision: str | None = "20260722_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create schedule definitions and their compact durable dispatch history."""

    op.create_table(
        "schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("search_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_type", sa.String(length=10), nullable=False),
        sa.Column("daily_time", sa.Time(), nullable=True),
        sa.Column("cron_expression", sa.String(length=100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("incremental", sa.Boolean(), nullable=False),
        sa.Column("retry_limit", sa.Integer(), nullable=False),
        sa.Column("last_dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["search_id"], ["searches.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedules_enabled", "schedules", ["enabled"], unique=False)
    op.create_index(
        "ix_schedules_enabled_trigger_type", "schedules", ["enabled", "trigger_type"], unique=False
    )
    op.create_index("ix_schedules_search_id", "schedules", ["search_id"], unique=False)
    op.create_table(
        "schedule_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=True),
        sa.Column("search_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("manual", sa.Boolean(), nullable=False),
        sa.Column("provider_run_count", sa.Integer(), nullable=False),
        sa.Column("failed_provider_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["search_id"], ["searches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_runs_schedule_created_at", "schedule_runs", ["schedule_id", "created_at"]
    )


def downgrade() -> None:
    """Remove schedule history and definitions."""

    op.drop_table("schedule_runs")
    op.drop_table("schedules")
