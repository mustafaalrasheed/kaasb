"""add payment_accounts transactions escrows tables

Revision ID: f88d375ec75a
Revises: f32778932130
Create Date: 2026-02-26 20:56:26.327499
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "f88d375ec75a"
down_revision = "f32778932130"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    q = conn.execute
    t = sa.text
    q(t("DO $x$ BEGIN CREATE TYPE paymentaccountstatus AS ENUM ('PENDING','ACTIVE','SUSPENDED','CLOSED'); EXCEPTION WHEN duplicate_object THEN NULL; END $x$;"))
    q(t("DO $x$ BEGIN CREATE TYPE transactiontype AS ENUM ('DEPOSIT','PAYMENT','RELEASE','WITHDRAWAL','REFUND','PLATFORM_FEE','DISPUTE_HOLD'); EXCEPTION WHEN duplicate_object THEN NULL; END $x$;"))
    q(t("DO $x$ BEGIN CREATE TYPE transactionstatus AS ENUM ('PENDING','PROCESSING','COMPLETED','FAILED','CANCELLED','REFUNDED'); EXCEPTION WHEN duplicate_object THEN NULL; END $x$;"))
    q(t("DO $x$ BEGIN CREATE TYPE escrowstatus AS ENUM ('FUNDED','RELEASED','REFUNDED','DISPUTED'); EXCEPTION WHEN duplicate_object THEN NULL; END $x$;"))
    q(t("CREATE TABLE IF NOT EXISTS payment_accounts (id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, stripe_customer_id VARCHAR(100), stripe_account_id VARCHAR(100), status paymentaccountstatus NOT NULL DEFAULT 'PENDING', available_balance FLOAT NOT NULL DEFAULT 0.0, pending_balance FLOAT NOT NULL DEFAULT 0.0, payout_enabled BOOLEAN NOT NULL DEFAULT FALSE, charges_enabled BOOLEAN NOT NULL DEFAULT FALSE, identity_verified BOOLEAN NOT NULL DEFAULT FALSE, verified_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())"))
    q(t("CREATE UNIQUE INDEX IF NOT EXISTS ix_payment_accounts_user_id ON payment_accounts (user_id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_payment_accounts_id ON payment_accounts (id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_payment_accounts_status ON payment_accounts (status)"))
    q(t("CREATE UNIQUE INDEX IF NOT EXISTS ix_payment_accounts_stripe_customer_id ON payment_accounts (stripe_customer_id) WHERE stripe_customer_id IS NOT NULL"))
    q(t("CREATE UNIQUE INDEX IF NOT EXISTS ix_payment_accounts_stripe_account_id ON payment_accounts (stripe_account_id) WHERE stripe_account_id IS NOT NULL"))
    q(t("CREATE TABLE IF NOT EXISTS escrows (id UUID PRIMARY KEY, client_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, freelancer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE, milestone_id UUID REFERENCES milestones(id) ON DELETE SET NULL, amount FLOAT NOT NULL, platform_fee FLOAT NOT NULL DEFAULT 0.0, currency VARCHAR(3) NOT NULL DEFAULT 'USD', status escrowstatus NOT NULL DEFAULT 'FUNDED', stripe_payment_intent_id VARCHAR(200), funded_at TIMESTAMPTZ, released_at TIMESTAMPTZ, refunded_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())"))
    q(t("CREATE INDEX IF NOT EXISTS ix_escrows_id ON escrows (id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_escrows_client_id ON escrows (client_id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_escrows_freelancer_id ON escrows (freelancer_id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_escrows_contract_id ON escrows (contract_id)"))
    q(t("CREATE UNIQUE INDEX IF NOT EXISTS ix_escrows_milestone_id ON escrows (milestone_id) WHERE milestone_id IS NOT NULL"))
    q(t("CREATE INDEX IF NOT EXISTS ix_escrows_status ON escrows (status)"))
    q(t("CREATE UNIQUE INDEX IF NOT EXISTS ix_escrows_stripe_payment_intent_id ON escrows (stripe_payment_intent_id) WHERE stripe_payment_intent_id IS NOT NULL"))
    q(t("CREATE TABLE IF NOT EXISTS transactions (id UUID PRIMARY KEY, from_user_id UUID REFERENCES users(id) ON DELETE SET NULL, to_user_id UUID REFERENCES users(id) ON DELETE SET NULL, type transactiontype NOT NULL, status transactionstatus NOT NULL DEFAULT 'PENDING', amount FLOAT NOT NULL, currency VARCHAR(3) NOT NULL DEFAULT 'USD', platform_fee FLOAT NOT NULL DEFAULT 0.0, net_amount FLOAT NOT NULL, stripe_payment_intent_id VARCHAR(200), stripe_transfer_id VARCHAR(200), stripe_charge_id VARCHAR(200), contract_id UUID REFERENCES contracts(id) ON DELETE SET NULL, milestone_id UUID REFERENCES milestones(id) ON DELETE SET NULL, description VARCHAR(500), failure_reason TEXT, completed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())"))
    q(t("CREATE INDEX IF NOT EXISTS ix_transactions_id ON transactions (id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_transactions_from_user_id ON transactions (from_user_id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_transactions_to_user_id ON transactions (to_user_id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_transactions_type ON transactions (type)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_transactions_status ON transactions (status)"))
    q(t("CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_stripe_payment_intent_id ON transactions (stripe_payment_intent_id) WHERE stripe_payment_intent_id IS NOT NULL"))
    q(t("CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_stripe_transfer_id ON transactions (stripe_transfer_id) WHERE stripe_transfer_id IS NOT NULL"))
    q(t("CREATE INDEX IF NOT EXISTS ix_transactions_stripe_charge_id ON transactions (stripe_charge_id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_transactions_contract_id ON transactions (contract_id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_transactions_milestone_id ON transactions (milestone_id)"))
    q(t("CREATE INDEX IF NOT EXISTS ix_transactions_type_status ON transactions (type, status)"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS transactions CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS escrows CASCADE"))
    conn.execute(sa.text("DROP TABLE IF EXISTS payment_accounts CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS escrowstatus CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS transactionstatus CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS transactiontype CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS paymentaccountstatus CASCADE"))
