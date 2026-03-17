"""qi_card_payment_integration

Revision ID: ae6a5c343032
Revises: 40dda097581c
Create Date: 2026-03-17 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'ae6a5c343032'
down_revision: Union[str, None] = '40dda097581c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'qi_card' to paymentprovider enum
    # PostgreSQL requires ALTER TYPE ... ADD VALUE (cannot be inside a transaction)
    op.execute("ALTER TYPE paymentprovider ADD VALUE IF NOT EXISTS 'qi_card'")

    # Add 'pending' to escrowstatus enum (for payments awaiting Qi Card confirmation)
    op.execute("ALTER TYPE escrowstatus ADD VALUE IF NOT EXISTS 'pending'")

    # Add Qi Card-specific columns to payment_accounts
    op.add_column(
        'payment_accounts',
        sa.Column('qi_card_phone', sa.String(20), nullable=True)
    )
    op.add_column(
        'payment_accounts',
        sa.Column('qi_card_payment_id', sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('payment_accounts', 'qi_card_payment_id')
    op.drop_column('payment_accounts', 'qi_card_phone')
    # Note: PostgreSQL does not support removing values from an enum.
    # To fully downgrade the enum, you would need to recreate it without 'qi_card'.
    # This is intentionally left as a no-op for safety.
