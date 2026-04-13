"""gig review audit trail and gig notification types

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-04-12

Changes:
- gigs.reviewed_by_id  FK → users.id (who approved/rejected)
- gigs.reviewed_at     TIMESTAMPTZ (when the decision was made)
- notificationtype enum: add gig_approved, gig_rejected, gig_submitted
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Add new values to the notificationtype enum ─────────────────────
    # Must be run outside a transaction block (PostgreSQL limitation for ALTER TYPE).
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'gig_approved'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'gig_rejected'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'gig_submitted'")

    # ── 2. Add audit columns to gigs ────────────────────────────────────────
    op.add_column(
        "gigs",
        sa.Column(
            "reviewed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "gigs",
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index("ix_gigs_reviewed_by_id", "gigs", ["reviewed_by_id"])


def downgrade() -> None:
    # ── 1. Drop audit columns ───────────────────────────────────────────────
    op.drop_index("ix_gigs_reviewed_by_id", table_name="gigs")
    op.drop_column("gigs", "reviewed_at")
    op.drop_column("gigs", "reviewed_by_id")

    # ── 2. Cannot remove enum values in PostgreSQL — downgrade is a no-op ──
    # The gig_approved / gig_rejected / gig_submitted enum values remain
    # in the DB but are unused by the application after downgrade.
