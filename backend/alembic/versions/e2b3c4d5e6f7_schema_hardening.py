"""schema_hardening

Fixes schema gaps discovered during production readiness audit:

1. users.deleted_at — column exists in the ORM model but was NEVER added to the
   database via any migration. Any code calling user.deleted_at is reading a
   Python-only attribute (always None) while the column doesn't exist in DB.

2. contracts.deleted_at — financial contracts must never be hard-deleted.
   Soft delete allows querying historical data while preserving audit trails.

3. audit_log table — append-only ledger tracking changes to sensitive tables
   (transactions, escrows, contracts, user roles). Required for financial
   compliance and forensic investigation.

4. escrows.funded_at nullable — EscrowStatus.PENDING was added in migration
   ae6a5c343032 for the Qi Card redirect flow, but funded_at is NOT NULL with
   no default. Creating a PENDING escrow requires a funded_at value, which is
   logically incorrect (the payment hasn't happened yet).

5. uq_conversation_no_job partial index — PostgreSQL treats NULL != NULL, so
   the existing UNIQUE(participant_one_id, participant_two_id, job_id) allows
   unlimited duplicate conversations when job_id IS NULL. This partial index
   enforces one-conversation-per-pair for direct messages.

Revision ID: e2b3c4d5e6f7
Revises: d1a2b3c4d5e6
Create Date: 2026-03-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'e2b3c4d5e6f7'
down_revision: Union[str, None] = 'd1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────────
    # 1. users.deleted_at — was in ORM model but never migrated to DB
    # ─────────────────────────────────────────────────────────────────────────
    op.add_column(
        'users',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Filtered index: only indexes non-NULL rows, keeping it tiny.
    # Queries checking "WHERE deleted_at IS NOT NULL" use this index.
    op.create_index(
        'ix_users_deleted_at_notnull',
        'users',
        ['deleted_at'],
        postgresql_where='deleted_at IS NOT NULL',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. contracts.deleted_at — soft delete for financial audit trail
    # ─────────────────────────────────────────────────────────────────────────
    op.add_column(
        'contracts',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. audit_log table — append-only change ledger
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        'audit_log',
        # Primary key
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),

        # What was changed
        sa.Column('table_name', sa.String(100), nullable=False),
        sa.Column('record_id',  sa.UUID(), nullable=False),
        sa.Column('action',     sa.String(10), nullable=False),  # INSERT | UPDATE | DELETE

        # Who changed it (NULL = system/background job)
        sa.Column('changed_by',  sa.UUID(), nullable=True),
        sa.Column('changed_at',  sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('ip_address',  sa.String(45), nullable=True),   # IPv4 or IPv6
        sa.Column('user_agent',  sa.String(500), nullable=True),

        # Before/after state (only changed fields, not full row)
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Constraints
        sa.CheckConstraint(
            "action IN ('INSERT', 'UPDATE', 'DELETE')",
            name='ck_audit_log_action',
        ),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Queries: "show me all changes to this record"
    op.create_index(
        'ix_audit_log_table_record',
        'audit_log',
        ['table_name', 'record_id'],
    )
    # Queries: "show me all changes made by this user"
    op.create_index(
        'ix_audit_log_changed_by',
        'audit_log',
        ['changed_by'],
    )
    # Queries: "show me recent audit events" — sorted by time descending
    op.create_index(
        'ix_audit_log_changed_at',
        'audit_log',
        [sa.text('changed_at DESC')],
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. escrows.funded_at: allow NULL for PENDING status
    # ─────────────────────────────────────────────────────────────────────────
    # Before: NOT NULL — impossible to insert a PENDING escrow (no funded_at yet).
    # After:  nullable — set to now() when status transitions to FUNDED.
    op.alter_column(
        'escrows',
        'funded_at',
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Conversations: prevent duplicate direct-message threads (NULL job_id)
    # ─────────────────────────────────────────────────────────────────────────
    # The existing UNIQUE(p1, p2, job_id) only prevents duplicate rows when
    # job_id IS NOT NULL (PostgreSQL: UNIQUE treats NULLs as distinct).
    # This partial unique index covers the IS NULL case.
    op.create_index(
        'uq_conversation_no_job',
        'conversations',
        ['participant_one_id', 'participant_two_id'],
        unique=True,
        postgresql_where='job_id IS NULL',
    )


def downgrade() -> None:
    op.drop_index('uq_conversation_no_job', table_name='conversations')

    op.alter_column(
        'escrows',
        'funded_at',
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )

    op.drop_index('ix_audit_log_changed_at', table_name='audit_log')
    op.drop_index('ix_audit_log_changed_by', table_name='audit_log')
    op.drop_index('ix_audit_log_table_record', table_name='audit_log')
    op.drop_table('audit_log')

    op.drop_column('contracts', 'deleted_at')

    op.drop_index('ix_users_deleted_at_notnull', table_name='users')
    op.drop_column('users', 'deleted_at')
