"""Add privacy-minimised resume skill profiles.

Revision ID: 20260723_0007
Revises: 20260722_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0007"
down_revision: str | None = "20260722_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the local resume-derived skill profile table."""

    op.create_table(
        "resume_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_version", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Remove locally derived resume skills."""

    op.drop_table("resume_profiles")
