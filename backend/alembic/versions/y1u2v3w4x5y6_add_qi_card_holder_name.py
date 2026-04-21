"""Add qi_card_holder_name to payment_accounts for payout matching

Revision ID: y1u2v3w4x5y6
Revises: x0s1t2u3v4w5
Create Date: 2026-04-21

QiCard exposes no payout API — the admin pays each freelancer manually via the
QiCard merchant portal / app. To reconcile manual payouts we need the cardholder
name on file so the admin can match ``qi_card_phone`` + ``qi_card_holder_name``
against the QiCard portal payee list. NULL-allowed for incremental onboarding;
service layer blocks escrow release to accounts where it is missing.
"""

import sqlalchemy as sa
from alembic import op

revision = "y1u2v3w4x5y6"
down_revision = "x0s1t2u3v4w5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_accounts",
        sa.Column("qi_card_holder_name", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_accounts", "qi_card_holder_name")
