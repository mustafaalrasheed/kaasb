"""gig needs_revision status and revision_note column

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-13

Changes:
- gigstatus enum: add needs_revision value
- gigs.revision_note  TEXT nullable (feedback from admin to freelancer)
- notificationtype enum: add gig_needs_revision value
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa

from alembic import op  # noqa: E402

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Add needs_revision to the gigstatus enum ─────────────────────────
    op.execute("ALTER TYPE gigstatus ADD VALUE IF NOT EXISTS 'needs_revision'")

    # ── 2. Add gig_needs_revision to notificationtype enum ──────────────────
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'gig_needs_revision'")

    # ── 3. Add revision_note column to gigs ─────────────────────────────────
    op.add_column(
        "gigs",
        sa.Column("revision_note", sa.Text, nullable=True),
    )


def downgrade() -> None:
    # Remove revision_note column
    op.drop_column("gigs", "revision_note")

    # PostgreSQL does not support removing enum values — downgrade is a no-op
    # for the enum changes. The values remain but are unused by the application.
