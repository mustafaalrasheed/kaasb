"""Chat system phase 1: conversation types, order link, sender role, system messages, attachments

Revision ID: i5d6e7f8g9h0
Revises: h4c5d6e7f8g9
Create Date: 2026-04-17

Introduces the foundation for a Fiverr/Upwork-style chat system:
  * conversation_type enum (user | order | support) so order chats and
    admin support threads are first-class and can be queried separately
    from peer-to-peer conversations.
  * conversations.order_id FK (→ gig_orders, SET NULL) for order chats.
  * messages.sender_role enum (client | freelancer | admin | system) so
    the UI can render the correct role badge independently of the sender's
    current primary_role (which may change over time).
  * messages.is_system flag for system-generated events (order placed,
    delivered, accepted, refunded, admin action, …).
  * messages.attachments JSONB array for file attachments (list of
    {url, filename, mime_type, size_bytes}).

The sender_role column is backfilled from users.primary_role for existing
rows, then set NOT NULL. conversation_type defaults to 'user' so existing
peer conversations stay peer conversations.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "i5d6e7f8g9h0"
down_revision: Union[str, None] = "h4c5d6e7f8g9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enums (idempotent) -------------------------------------------------
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE conversationtype AS ENUM ('user', 'order', 'support'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE senderrole AS ENUM ('client', 'freelancer', 'admin', 'system'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    # --- conversations ------------------------------------------------------
    op.add_column(
        "conversations",
        sa.Column(
            "conversation_type",
            postgresql.ENUM(
                "user", "order", "support",
                name="conversationtype", create_type=False,
            ),
            nullable=False,
            server_default="user",
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_order_id",
        "conversations", "gig_orders",
        ["order_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversations_order_id", "conversations", ["order_id"],
    )
    op.create_index(
        "ix_conversations_type", "conversations", ["conversation_type"],
    )

    # --- messages -----------------------------------------------------------
    # Add as nullable first, backfill, then set NOT NULL.
    op.add_column(
        "messages",
        sa.Column(
            "sender_role",
            postgresql.ENUM(
                "client", "freelancer", "admin", "system",
                name="senderrole", create_type=False,
            ),
            nullable=True,
        ),
    )
    # Backfill: admin if is_superuser, else primary_role. Cast via text.
    op.execute(
        """
        UPDATE messages m
        SET sender_role = (
            CASE
                WHEN u.is_superuser THEN 'admin'
                ELSE u.primary_role::text
            END
        )::senderrole
        FROM users u
        WHERE m.sender_id = u.id AND m.sender_role IS NULL
        """
    )
    op.alter_column("messages", "sender_role", nullable=False)

    op.add_column(
        "messages",
        sa.Column(
            "is_system", sa.Boolean(), nullable=False, server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "messages",
        sa.Column(
            "attachments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "attachments")
    op.drop_column("messages", "is_system")
    op.drop_column("messages", "sender_role")

    op.drop_index("ix_conversations_type", table_name="conversations")
    op.drop_index("ix_conversations_order_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_order_id", "conversations", type_="foreignkey",
    )
    op.drop_column("conversations", "order_id")
    op.drop_column("conversations", "conversation_type")

    op.execute("DROP TYPE IF EXISTS senderrole")
    op.execute("DROP TYPE IF EXISTS conversationtype")
