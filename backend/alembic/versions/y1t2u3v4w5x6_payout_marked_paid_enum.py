"""Add payout_marked_paid to adminauditaction enum

Revision ID: y1t2u3v4w5x6
Revises: b4x5y6z7a8b9
Create Date: 2026-04-21

Supports the new admin "Mark Paid" action on freelancer-initiated payouts:
after the admin manually sends the money via the Qi Card merchant dashboard
and flips the PAYOUT transaction from PROCESSING to COMPLETED in Kaasb, an
audit row is written with action=PAYOUT_MARKED_PAID.
"""

from alembic import op

revision = "y1t2u3v4w5x6"
down_revision = "b4x5y6z7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE must run outside a transaction. Idempotent via
    # IF NOT EXISTS so the migration can be re-applied without exploding.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE adminauditaction ADD VALUE IF NOT EXISTS 'payout_marked_paid'"
        )


def downgrade() -> None:
    # Postgres does not support removing enum values without dropping + recreating
    # the entire type. Any existing rows referencing the value would also need
    # rewriting. Treat this migration as forward-only; no-op on downgrade.
    pass
