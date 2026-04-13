"""Wire gig orders to Qi Card payment / escrow

Revision ID: g3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-04-14

Changes:
- escrows.contract_id  → nullable=True  (was NOT NULL; now supports gig-order escrows)
- escrows.milestone_id → nullable=True  (same reason)
- escrows.gig_order_id TEXT FK → gig_orders.id (nullable, unique when non-null)
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "g3b4c5d6e7f8"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Make existing FK columns nullable
    op.alter_column("escrows", "contract_id", nullable=True)
    op.alter_column("escrows", "milestone_id", nullable=True)

    # 2. Add gig_order_id column
    op.add_column(
        "escrows",
        sa.Column(
            "gig_order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("gig_orders.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )

    # 3. Index for fast lookup
    op.create_index("ix_escrows_gig_order_id", "escrows", ["gig_order_id"])

    # 4. Unique constraint (NULL values don't conflict — Postgres treats each NULL as distinct)
    op.create_unique_constraint("uq_escrow_gig_order", "escrows", ["gig_order_id"])


def downgrade() -> None:
    op.drop_constraint("uq_escrow_gig_order", "escrows", type_="unique")
    op.drop_index("ix_escrows_gig_order_id", table_name="escrows")
    op.drop_column("escrows", "gig_order_id")
    op.alter_column("escrows", "milestone_id", nullable=False)
    op.alter_column("escrows", "contract_id", nullable=False)
