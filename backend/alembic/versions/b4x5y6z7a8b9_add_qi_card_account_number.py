"""Add qi_card_account_number to payment_accounts — unique per QiCard

Revision ID: b4x5y6z7a8b9
Revises: a3w4x5y6z7a8
Create Date: 2026-04-24

Chained behind a3w4x5y6z7a8 (chat conversation partial uniq indexes).

Per user feedback 2026-04-24: one Iraqi can have multiple QiCards on the same
phone number (same holder, different cards), so ``qi_card_phone`` alone is not
a unique destination identifier for a payout. The QiCard mobile app's Transfer
flow resolves the account from the phone — if multiple cards match, the admin
risks paying the wrong one. Adding ``qi_card_account_number`` as the unique
per-card identifier. Freelancers fill it in on /dashboard/payments alongside
phone + holder name; the service-layer release guard checks all three are
present before allowing escrow release.

NULL-allowed initially for incremental onboarding — existing payment_accounts
rows don't get blocked retroactively. The guard in ``release_escrow_by_id``
will reject payouts where it's missing (same pattern as qi_card_holder_name).
"""

import sqlalchemy as sa
from alembic import op

revision = "b4x5y6z7a8b9"
down_revision = "a3w4x5y6z7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_accounts",
        sa.Column("qi_card_account_number", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_accounts", "qi_card_account_number")
