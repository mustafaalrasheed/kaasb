"""qi_card_only_payments

Remove Stripe and Wise support — Qi Card is the sole payment gateway.

Changes:
1. Drop wise_email and wise_currency columns from payment_accounts
2. Recreate paymentprovider enum with only 'qi_card' and 'manual' values

Revision ID: b2c3d4e5f6a7
Revises: f3a4b5c6d7e8
Create Date: 2026-03-30
"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop Wise-specific columns (no longer needed)
    op.drop_column("payment_accounts", "wise_email")
    op.drop_column("payment_accounts", "wise_currency")

    # Recreate paymentprovider enum without stripe and wise.
    # PostgreSQL does not support DROP VALUE on enums, so we recreate the type.
    op.execute(
        "DELETE FROM payment_accounts WHERE provider IN ('stripe', 'wise')"
    )
    op.execute(
        "DELETE FROM transactions WHERE provider IN ('stripe', 'wise')"
    )

    # Temporarily cast columns to text, swap enum, cast back
    op.execute(
        "ALTER TABLE payment_accounts ALTER COLUMN provider TYPE text USING provider::text"
    )
    op.execute(
        "ALTER TABLE transactions ALTER COLUMN provider TYPE text USING provider::text"
    )

    op.execute("DROP TYPE IF EXISTS paymentprovider")
    op.execute("CREATE TYPE paymentprovider AS ENUM ('manual', 'qi_card')")

    op.execute(
        "ALTER TABLE payment_accounts ALTER COLUMN provider "
        "TYPE paymentprovider USING provider::paymentprovider"
    )
    op.execute(
        "ALTER TABLE transactions ALTER COLUMN provider "
        "TYPE paymentprovider USING provider::paymentprovider"
    )


def downgrade() -> None:
    # Restore wise columns
    op.add_column(
        "payment_accounts",
        sa.Column("wise_email", sa.String(255), nullable=True),
    )
    op.add_column(
        "payment_accounts",
        sa.Column("wise_currency", sa.String(3), nullable=False, server_default="USD"),
    )

    # Restore full enum
    op.execute(
        "ALTER TABLE payment_accounts ALTER COLUMN provider TYPE text USING provider::text"
    )
    op.execute(
        "ALTER TABLE transactions ALTER COLUMN provider TYPE text USING provider::text"
    )

    op.execute("DROP TYPE IF EXISTS paymentprovider")
    op.execute("CREATE TYPE paymentprovider AS ENUM ('stripe', 'wise', 'manual', 'qi_card')")

    op.execute(
        "ALTER TABLE payment_accounts ALTER COLUMN provider "
        "TYPE paymentprovider USING provider::paymentprovider"
    )
    op.execute(
        "ALTER TABLE transactions ALTER COLUMN provider "
        "TYPE paymentprovider USING provider::paymentprovider"
    )
