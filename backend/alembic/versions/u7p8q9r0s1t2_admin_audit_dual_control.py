"""Admin audit log + payout dual-control

Revision ID: u7p8q9r0s1t2
Revises: t6o7p8q9r0s1
Create Date: 2026-04-20

- New table: admin_audit_logs (append-only admin action record)
- New table: payout_approvals (two-admin approval queue for high-value releases)
- Enums: adminauditaction, payoutapprovalstatus
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "u7p8q9r0s1t2"
down_revision = "t6o7p8q9r0s1"
branch_labels = None
depends_on = None


_AUDIT_ACTIONS = (
    "escrow_release_requested",
    "escrow_released",
    "escrow_refunded",
    "payout_approved",
    "payout_rejected",
    "user_status_changed",
    "user_promoted_admin",
    "user_demoted_admin",
    "user_promoted_support",
    "user_demoted_support",
    "gig_approved",
    "gig_rejected",
    "dispute_resolved",
)

_APPROVAL_STATUSES = ("pending", "approved", "rejected", "cancelled")


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN CREATE TYPE adminauditaction AS ENUM ("
        + ", ".join(f"'{v}'" for v in _AUDIT_ACTIONS)
        + "); EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE payoutapprovalstatus AS ENUM ("
        + ", ".join(f"'{v}'" for v in _APPROVAL_STATUSES)
        + "); EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "action",
            postgresql.ENUM(*_AUDIT_ACTIONS, name="adminauditaction", create_type=False),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(12, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_logs_id", "admin_audit_logs", ["id"])
    op.create_index("ix_admin_audit_logs_admin_id", "admin_audit_logs", ["admin_id"])
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.create_index(
        "ix_admin_audit_logs_admin_created",
        "admin_audit_logs",
        ["admin_id", "created_at"],
    )
    op.create_index(
        "ix_admin_audit_logs_target",
        "admin_audit_logs",
        ["target_type", "target_id"],
    )

    op.create_table(
        "payout_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("escrow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="IQD", nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(*_APPROVAL_STATUSES, name="payoutapprovalstatus", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("request_note", sa.Text(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["escrow_id"], ["escrows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("amount > 0", name="ck_payout_approval_amount_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payout_approvals_id", "payout_approvals", ["id"])
    op.create_index("ix_payout_approvals_escrow_id", "payout_approvals", ["escrow_id"])
    op.create_index("ix_payout_approvals_requested_by_id", "payout_approvals", ["requested_by_id"])
    op.create_index("ix_payout_approvals_status", "payout_approvals", ["status"])
    # Only one active (pending) approval per escrow at a time.
    op.create_index(
        "uq_payout_approvals_escrow_active",
        "payout_approvals",
        ["escrow_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_payout_approvals_escrow_active", table_name="payout_approvals")
    op.drop_index("ix_payout_approvals_status", table_name="payout_approvals")
    op.drop_index("ix_payout_approvals_requested_by_id", table_name="payout_approvals")
    op.drop_index("ix_payout_approvals_escrow_id", table_name="payout_approvals")
    op.drop_index("ix_payout_approvals_id", table_name="payout_approvals")
    op.drop_table("payout_approvals")

    op.drop_index("ix_admin_audit_logs_target", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_admin_created", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_action", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_admin_id", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_id", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")

    op.execute("DROP TYPE IF EXISTS payoutapprovalstatus")
    op.execute("DROP TYPE IF EXISTS adminauditaction")
