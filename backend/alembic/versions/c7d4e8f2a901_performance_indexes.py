"""performance_indexes

Add composite and covering indexes for all high-traffic query patterns.
These indexes target the exact WHERE + ORDER BY combinations used in
search, listing, and filtering endpoints across the platform.

Estimated impact: 5-50x faster on filtered/sorted queries at scale.

Revision ID: c7d4e8f2a901
Revises: b3f9e2a1c456
Create Date: 2026-03-25 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c7d4e8f2a901'
down_revision: Union[str, None] = 'b3f9e2a1c456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── JOBS ──────────────────────────────────────────────────────────
    # Job search: WHERE status='open' ORDER BY published_at DESC (most common query)
    op.create_index(
        'ix_jobs_status_published',
        'jobs',
        ['status', sa.text('published_at DESC')],
        postgresql_where="status = 'open'",
    )
    # Job search by category + status
    op.create_index('ix_jobs_status_category', 'jobs', ['status', 'category'])
    # Client's jobs: WHERE client_id=? ORDER BY created_at DESC
    op.create_index('ix_jobs_client_created', 'jobs', ['client_id', sa.text('created_at DESC')])

    # ── PROPOSALS ─────────────────────────────────────────────────────
    # Freelancer's proposals: WHERE freelancer_id=? ORDER BY submitted_at DESC
    op.create_index('ix_proposals_freelancer_submitted', 'proposals', ['freelancer_id', sa.text('submitted_at DESC')])
    # Job proposals listing: WHERE job_id=? AND status=? ORDER BY submitted_at DESC
    op.create_index('ix_proposals_job_status', 'proposals', ['job_id', 'status'])

    # ── CONTRACTS ─────────────────────────────────────────────────────
    # "My contracts" for client or freelancer, ordered by started_at DESC
    op.create_index('ix_contracts_client_started', 'contracts', ['client_id', sa.text('started_at DESC')])
    op.create_index('ix_contracts_freelancer_started', 'contracts', ['freelancer_id', sa.text('started_at DESC')])

    # ── MILESTONES ────────────────────────────────────────────────────
    # Milestones by contract, ordered for display
    op.create_index('ix_milestones_contract_order', 'milestones', ['contract_id', 'order'])

    # ── NOTIFICATIONS ─────────────────────────────────────────────────
    # User's notifications: WHERE user_id=? AND is_read=false ORDER BY created_at DESC
    # Composite index covers both "all" and "unread only" queries
    op.create_index('ix_notifications_user_read_created', 'notifications', ['user_id', 'is_read', sa.text('created_at DESC')])

    # ── MESSAGES ──────────────────────────────────────────────────────
    # Messages in conversation: WHERE conversation_id=? ORDER BY created_at DESC
    op.create_index('ix_messages_conversation_created', 'messages', ['conversation_id', sa.text('created_at DESC')])

    # ── CONVERSATIONS ─────────────────────────────────────────────────
    # User's conversations ordered by last activity
    op.create_index('ix_conversations_p1_last_msg', 'conversations', ['participant_one_id', sa.text('last_message_at DESC')])
    op.create_index('ix_conversations_p2_last_msg', 'conversations', ['participant_two_id', sa.text('last_message_at DESC')])

    # ── REVIEWS ───────────────────────────────────────────────────────
    # Reviews for a user (public only): WHERE reviewee_id=? AND is_public=true ORDER BY created_at DESC
    op.create_index('ix_reviews_reviewee_public', 'reviews', ['reviewee_id', 'is_public', sa.text('created_at DESC')])

    # ── TRANSACTIONS ──────────────────────────────────────────────────
    # Admin transaction listing + financial aggregation queries
    op.create_index('ix_transactions_type_status', 'transactions', ['transaction_type', 'status'])
    # User's transactions: WHERE payer_id=? OR payee_id=? ORDER BY created_at DESC
    op.create_index('ix_transactions_payer_created', 'transactions', ['payer_id', sa.text('created_at DESC')])
    op.create_index('ix_transactions_payee_created', 'transactions', ['payee_id', sa.text('created_at DESC')])

    # ── ESCROWS ───────────────────────────────────────────────────────
    # Escrow lookup by milestone (1:1 relationship, used in release_escrow)
    op.create_index('ix_escrows_milestone_status', 'escrows', ['milestone_id', 'status'])

    # ── REFRESH TOKENS ────────────────────────────────────────────────
    # Token lookup: WHERE token_hash=? AND revoked=false AND expires_at > now()
    op.create_index('ix_refresh_tokens_hash_active', 'refresh_tokens', ['token_hash', 'revoked', 'expires_at'])
    # Cleanup expired tokens
    op.create_index('ix_refresh_tokens_expires', 'refresh_tokens', ['expires_at'])
    # Revoke all for user
    op.create_index('ix_refresh_tokens_user_revoked', 'refresh_tokens', ['user_id', 'revoked'])

    # ── USERS ─────────────────────────────────────────────────────────
    # Freelancer search: WHERE primary_role='freelancer' AND status='active'
    op.create_index(
        'ix_users_freelancer_active',
        'users',
        ['primary_role', 'status'],
        postgresql_where="primary_role = 'freelancer' AND status = 'active'",
    )
    # Admin user listing sorted by created_at
    op.create_index('ix_users_role_status_created', 'users', ['primary_role', 'status', sa.text('created_at DESC')])


def downgrade() -> None:
    # Drop all indexes in reverse order
    op.drop_index('ix_users_role_status_created', table_name='users')
    op.drop_index('ix_users_freelancer_active', table_name='users')
    op.drop_index('ix_refresh_tokens_user_revoked', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_expires', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_hash_active', table_name='refresh_tokens')
    op.drop_index('ix_escrows_milestone_status', table_name='escrows')
    op.drop_index('ix_transactions_payee_created', table_name='transactions')
    op.drop_index('ix_transactions_payer_created', table_name='transactions')
    op.drop_index('ix_transactions_type_status', table_name='transactions')
    op.drop_index('ix_reviews_reviewee_public', table_name='reviews')
    op.drop_index('ix_conversations_p2_last_msg', table_name='conversations')
    op.drop_index('ix_conversations_p1_last_msg', table_name='conversations')
    op.drop_index('ix_messages_conversation_created', table_name='messages')
    op.drop_index('ix_notifications_user_read_created', table_name='notifications')
    op.drop_index('ix_milestones_contract_order', table_name='milestones')
    op.drop_index('ix_contracts_freelancer_started', table_name='contracts')
    op.drop_index('ix_contracts_client_started', table_name='contracts')
    op.drop_index('ix_proposals_job_status', table_name='proposals')
    op.drop_index('ix_proposals_freelancer_submitted', table_name='proposals')
    op.drop_index('ix_jobs_client_created', table_name='jobs')
    op.drop_index('ix_jobs_status_category', table_name='jobs')
    op.drop_index('ix_jobs_status_published', table_name='jobs')
