"""Add privacy-minimised export audit events.

Revision ID: 20260722_0003
Revises: 20260722_0002
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0003"
down_revision: str | None = "20260722_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create durable export event metadata without recording job descriptions or filters."""

    op.create_table(
        "export_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("resource", sa.String(length=32), nullable=False),
        sa.Column("selected_job_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_events_format", "export_events", ["format"], unique=False)
    op.create_index("ix_export_events_created_at", "export_events", ["created_at"], unique=False)


def downgrade() -> None:
    """Remove export audit metadata without changing job records."""

    op.drop_table("export_events")
