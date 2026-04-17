"""Rename conversation_type index to match SQLAlchemy auto-generated name

Revision ID: k7f8g9h0i1j2
Revises: j6e7f8g9h0i1
Create Date: 2026-04-18

Phase 1 (migration ``i5d6e7f8g9h0``) created the index with name
``ix_conversations_type`` but the model declares ``index=True`` on
``conversation_type``, which SQLAlchemy expects to materialise as
``ix_conversations_conversation_type``. That mismatch made ``alembic check``
fail on CI. Rename the index so the DB state matches the model.
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "k7f8g9h0i1j2"
down_revision: Union[str, None] = "j6e7f8g9h0i1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER INDEX IF EXISTS ix_conversations_type "
        "RENAME TO ix_conversations_conversation_type"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX IF EXISTS ix_conversations_conversation_type "
        "RENAME TO ix_conversations_type"
    )
