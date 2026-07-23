"""Add durable user workflow state for the job workspace.

Revision ID: 20260722_0002
Revises: 20260722_0001
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0002"
down_revision: str | None = "20260722_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create optional bookmark, application, and note state for each job."""

    op.create_table(
        "job_workflows",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("is_bookmarked", sa.Boolean(), nullable=False),
        sa.Column("is_applied", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_job_workflows_is_bookmarked", "job_workflows", ["is_bookmarked"])
    op.create_index("ix_job_workflows_is_applied", "job_workflows", ["is_applied"])
    op.create_index(
        "ix_job_workflows_bookmarked_updated_at",
        "job_workflows",
        ["is_bookmarked", "updated_at"],
    )
    op.create_index(
        "ix_job_workflows_applied_updated_at",
        "job_workflows",
        ["is_applied", "updated_at"],
    )


def downgrade() -> None:
    """Remove job workflow state without touching source job records."""

    op.drop_table("job_workflows")
