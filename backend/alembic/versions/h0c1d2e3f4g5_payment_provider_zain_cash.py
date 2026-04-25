"""Add zain_cash to paymentprovider enum

Revision ID: h0c1d2e3f4g5
Revises: g9b0c1d2e3f4
Create Date: 2026-04-25

Wires up the second payment gateway: Zain Cash mobile-money. Existing
``transactions.provider`` and ``escrows.provider`` columns use the
``paymentprovider`` Postgres enum; we just need a new value. No
column changes — call sites pick the provider at fund-escrow time and
the rest of the schema is gateway-agnostic.

ALTER TYPE ... ADD VALUE can't run inside a transaction in older
Postgres versions; use Alembic's ``autocommit_block`` (same pattern
as g9b0c1d2e3f4 and the original ae6a5c343032 qi_card migration).
"""

from alembic import op

revision = "h0c1d2e3f4g5"
down_revision = "g9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE paymentprovider ADD VALUE IF NOT EXISTS 'zain_cash'"
        )


def downgrade() -> None:
    # Postgres does not support DROP VALUE on an enum. The variant is left
    # in place on downgrade — nothing references it once code rolls back.
    pass
