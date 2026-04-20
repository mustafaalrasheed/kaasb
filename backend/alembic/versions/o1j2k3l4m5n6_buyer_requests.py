"""Add buyer_requests and buyer_request_offers tables

Revision ID: o1j2k3l4m5n6
Revises: n0i1j2k3l4m5
Create Date: 2026-04-20

Feature: Buyer Requests (Fiverr-style "Post a Request")
  - Clients post short briefs; freelancers browse and send offers.
  - Max 10 active requests per client, max 10 offers per request.
  - Requests auto-expire after 7 days.
  - Notification types: buyer_request_offer_received/accepted/rejected
    and future F3/F4/F2/F6 notification types added here so all enum
    additions live in a single migration.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "o1j2k3l4m5n6"
down_revision = "n0i1j2k3l4m5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── New enum types ─────────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE buyerrequeststatus AS ENUM ('open', 'filled', 'expired', 'cancelled');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE buyerrequestofferstatus AS ENUM ('pending', 'accepted', 'rejected');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── buyer_requests ─────────────────────────────────────────────────────
    op.create_table(
        "buyer_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("budget_min", sa.Numeric(12, 2), nullable=False),
        sa.Column("budget_max", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_days", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("open", "filled", "expired", "cancelled",
                            name="buyerrequeststatus", create_type=False),
            nullable=False,
            server_default="open",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["gig_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buyer_requests_client_id", "buyer_requests", ["client_id"])
    op.create_index("ix_buyer_requests_status", "buyer_requests", ["status"])
    op.create_index("ix_buyer_requests_category_id", "buyer_requests", ["category_id"])

    # ── buyer_request_offers ───────────────────────────────────────────────
    op.create_table(
        "buyer_request_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("freelancer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gig_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_days", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "accepted", "rejected",
                            name="buyerrequestofferstatus", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["buyer_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["freelancer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["gig_id"], ["gigs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buyer_request_offers_request_id", "buyer_request_offers", ["request_id"])
    op.create_index("ix_buyer_request_offers_freelancer_id", "buyer_request_offers", ["freelancer_id"])
    op.create_index("ix_buyer_request_offers_status", "buyer_request_offers", ["status"])

    # ── New notification types ─────────────────────────────────────────────
    # Feature 1 (buyer requests)
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'buyer_request_offer_received'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'buyer_request_offer_accepted'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'buyer_request_offer_rejected'")
    # Feature 3 (order requirements)
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'order_requirements_submitted'")
    # Feature 4 (structured delivery)
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'order_delivered'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'order_auto_completed'")
    # Feature 2 (seller levels)
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'seller_level_upgraded'")
    # Feature 6 (anti off-platform)
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'chat_violation_warning'")


def downgrade() -> None:
    op.drop_index("ix_buyer_request_offers_status", "buyer_request_offers")
    op.drop_index("ix_buyer_request_offers_freelancer_id", "buyer_request_offers")
    op.drop_index("ix_buyer_request_offers_request_id", "buyer_request_offers")
    op.drop_table("buyer_request_offers")

    op.drop_index("ix_buyer_requests_category_id", "buyer_requests")
    op.drop_index("ix_buyer_requests_status", "buyer_requests")
    op.drop_index("ix_buyer_requests_client_id", "buyer_requests")
    op.drop_table("buyer_requests")

    op.execute("DROP TYPE IF EXISTS buyerrequestofferstatus")
    op.execute("DROP TYPE IF EXISTS buyerrequeststatus")
    # Note: PostgreSQL enum values cannot be removed — notification type downgrade is a no-op.
