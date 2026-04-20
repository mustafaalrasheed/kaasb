"""Add order requirements, delivery records, and gig ranking

Revision ID: q3l4m5n6o1p2
Revises: p2k3l4m5n6o1
Create Date: 2026-04-20

Feature 3: Order Requirements Flow
  - gigs.requirement_questions JSONB — freelancer's question template
  - gig_orders.requirement_answers JSONB — client's structured answers
  - gig_orders.requirements_submitted_at TIMESTAMPTZ
  - gigorderstatus ADD VALUE 'pending_requirements'

Feature 4: Structured Delivery
  - New table gig_order_deliveries (id, order_id, message, files, revision_number)

Feature 7: Gig Ranking
  - gigs.rank_score NUMERIC(6,2) — daily-calculated score (0–100)
  - gigs.rank_updated_at TIMESTAMPTZ
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "q3l4m5n6o1p2"
down_revision = "p2k3l4m5n6o1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── F3: gigorderstatus new value ───────────────────────────────────────
    op.execute(
        "ALTER TYPE gigorderstatus ADD VALUE IF NOT EXISTS 'pending_requirements'"
    )

    # ── F3: gigs ───────────────────────────────────────────────────────────
    op.add_column("gigs", sa.Column("requirement_questions", postgresql.JSONB(), nullable=True))

    # ── F3: gig_orders ─────────────────────────────────────────────────────
    op.add_column("gig_orders", sa.Column("requirement_answers", postgresql.JSONB(), nullable=True))
    op.add_column("gig_orders", sa.Column("requirements_submitted_at", sa.DateTime(timezone=True), nullable=True))

    # ── F4: gig_order_deliveries ───────────────────────────────────────────
    op.create_table(
        "gig_order_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("files", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["gig_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gig_order_deliveries_order_id", "gig_order_deliveries", ["order_id"])

    # ── F7: gigs rank_score ────────────────────────────────────────────────
    op.add_column(
        "gigs",
        sa.Column("rank_score", sa.Numeric(6, 2), nullable=False, server_default="0"),
    )
    op.add_column("gigs", sa.Column("rank_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_gigs_rank_score", "gigs", ["rank_score"])


def downgrade() -> None:
    op.drop_index("ix_gigs_rank_score", "gigs")
    op.drop_column("gigs", "rank_updated_at")
    op.drop_column("gigs", "rank_score")

    op.drop_index("ix_gig_order_deliveries_order_id", "gig_order_deliveries")
    op.drop_table("gig_order_deliveries")

    op.drop_column("gig_orders", "requirements_submitted_at")
    op.drop_column("gig_orders", "requirement_answers")
    op.drop_column("gigs", "requirement_questions")
    # Note: cannot remove 'pending_requirements' from gigorderstatus enum in PostgreSQL
