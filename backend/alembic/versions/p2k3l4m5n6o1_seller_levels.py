"""Add seller_level and performance columns to users

Revision ID: p2k3l4m5n6o1
Revises: o1j2k3l4m5n6
Create Date: 2026-04-20

Feature 2: Seller Levels
  - Freelancers earn levels based on completed orders, rating,
    completion rate, and response rate.
  - Levels: new_seller → level_1 → level_2 → top_rated (manual only)
  - Recalculated daily by app.tasks.marketplace_tasks

Feature 6 (anti off-platform) user columns also included here:
  - chat_violations: int
  - chat_suspended_until: timestamptz
"""

import sqlalchemy as sa
from alembic import op

revision = "p2k3l4m5n6o1"
down_revision = "o1j2k3l4m5n6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sellerlevel enum ───────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE sellerlevel AS ENUM ('new_seller', 'level_1', 'level_2', 'top_rated');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── Seller level columns ───────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "seller_level",
            sa.Enum("new_seller", "level_1", "level_2", "top_rated",
                    name="sellerlevel", create_type=False),
            nullable=False,
            server_default="new_seller",
        ),
    )
    op.add_column("users", sa.Column("total_completed_orders", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("completion_rate", sa.Numeric(5, 4), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("response_rate", sa.Numeric(5, 4), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("avg_response_time_hours", sa.Numeric(8, 2), nullable=True))
    op.add_column("users", sa.Column("level_updated_at", sa.DateTime(timezone=True), nullable=True))

    # ── Anti off-platform columns (F6) ────────────────────────────────────
    op.add_column("users", sa.Column("chat_violations", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("chat_suspended_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "chat_suspended_until")
    op.drop_column("users", "chat_violations")
    op.drop_column("users", "level_updated_at")
    op.drop_column("users", "avg_response_time_hours")
    op.drop_column("users", "response_rate")
    op.drop_column("users", "completion_rate")
    op.drop_column("users", "total_completed_orders")
    op.drop_column("users", "seller_level")
    op.execute("DROP TYPE IF EXISTS sellerlevel")
