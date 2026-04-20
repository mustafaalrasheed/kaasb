"""Add dedicated disputes table (F5)

Revision ID: r4m5n6o1p2q3
Revises: q3l4m5n6o1p2
Create Date: 2026-04-20

Feature 5: Dispute Resolution System
  - New table: disputes
  - Enums: disputereason, disputestatus
  - One dispute per order (unique on order_id)
  - Supports admin assignment, evidence files, resolution notes
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "r4m5n6o1p2q3"
down_revision = "q3l4m5n6o1p2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE disputereason AS ENUM (
                'quality', 'deadline', 'communication', 'not_as_described', 'other'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE disputestatus AS ENUM (
                'open', 'under_review', 'resolved_refund', 'resolved_release', 'cancelled'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.create_table(
        "disputes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("initiated_by", sa.String(20), nullable=False),
        sa.Column(
            "reason",
            postgresql.ENUM(
                "quality", "deadline", "communication", "not_as_described", "other",
                name="disputereason", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_files", sa.ARRAY(sa.String()), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "open", "under_review", "resolved_refund", "resolved_release", "cancelled",
                name="disputestatus", create_type=False,
            ),
            nullable=False,
            server_default="open",
        ),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["gig_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_dispute_order_id"),
    )
    op.create_index("ix_disputes_order_id", "disputes", ["order_id"])
    op.create_index("ix_disputes_status", "disputes", ["status"])


def downgrade() -> None:
    op.drop_index("ix_disputes_status", "disputes")
    op.drop_index("ix_disputes_order_id", "disputes")
    op.drop_table("disputes")
    op.execute("DROP TYPE IF EXISTS disputestatus")
    op.execute("DROP TYPE IF EXISTS disputereason")
