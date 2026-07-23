"""Add privacy-minimised notification delivery history.

Revision ID: 20260722_0006
Revises: 20260722_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0006"
down_revision: str | None = "20260722_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create safe notification delivery audit metadata."""
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_category", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_deliveries_channel", "notification_deliveries", ["channel"])
    op.create_index(
        "ix_notification_deliveries_created_at", "notification_deliveries", ["created_at"]
    )


def downgrade() -> None:
    """Remove notification history."""
    op.drop_table("notification_deliveries")
