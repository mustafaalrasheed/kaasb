"""Dispute system: add dispute columns to gig_orders and notification types

Revision ID: m9h0i1j2k3l4
Revises: l8g9h0i1j2k3
Create Date: 2026-04-19

Adds dispute tracking columns to gig_orders so clients can raise disputes on
active or delivered orders.  Also adds DISPUTE_OPENED and DISPUTE_RESOLVED to the
notification_type PostgreSQL enum.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "m9h0i1j2k3l4"
down_revision = "l8g9h0i1j2k3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- notification_type enum: add dispute values ---
    op.execute(
        """
        ALTER TYPE notificationtype
          ADD VALUE IF NOT EXISTS 'dispute_opened';
        """
    )
    op.execute(
        """
        ALTER TYPE notificationtype
          ADD VALUE IF NOT EXISTS 'dispute_resolved';
        """
    )

    # --- gig_orders: add dispute columns ---
    op.add_column("gig_orders", sa.Column("dispute_reason", sa.Text(), nullable=True))
    op.add_column(
        "gig_orders",
        sa.Column("dispute_opened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "gig_orders",
        sa.Column(
            "dispute_opened_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "gig_orders",
        sa.Column("dispute_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "gig_orders",
        sa.Column("dispute_resolution", sa.String(50), nullable=True),
    )

    # Index for admin dispute queue
    op.create_index(
        "ix_gig_orders_dispute_opened_at",
        "gig_orders",
        ["dispute_opened_at"],
        postgresql_where=sa.text("dispute_opened_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_gig_orders_dispute_opened_at", table_name="gig_orders")
    op.drop_column("gig_orders", "dispute_resolution")
    op.drop_column("gig_orders", "dispute_resolved_at")
    op.drop_column("gig_orders", "dispute_opened_by")
    op.drop_column("gig_orders", "dispute_opened_at")
    op.drop_column("gig_orders", "dispute_reason")
    # Enum values cannot be removed from PostgreSQL enums without recreating the type.
