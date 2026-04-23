"""Integration test — F6 anti-off-platform filter through MessageService.send_message.

Unit tests in tests/unit/test_message_filter*.py exhaustively cover the
regex / detection / masking logic. This integration test verifies that
the filter is actually *invoked* by send_message end-to-end:
- Clean message goes through untouched
- Message containing an email triggers the filter and returns a
  FilterOutcome with a non-zero violation count

The filter mutates user.chat_violations, so tests are scoped to a fresh
user via conftest's autouse schema-drop — state doesn't leak.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Conversation, ConversationType
from app.models.user import User
from app.schemas.message import MessageCreate
from app.services.message_service import MessageService


@pytest_asyncio.fixture
async def user_conversation(
    db_session: AsyncSession,
    sample_client_user: User,
    sample_freelancer_user: User,
) -> Conversation:
    """A USER-type conversation between the sample client and freelancer."""
    conv = Conversation(
        id=uuid.uuid4(),
        participant_one_id=sample_client_user.id,
        participant_two_id=sample_freelancer_user.id,
        conversation_type=ConversationType.USER,
    )
    db_session.add(conv)
    await db_session.flush()
    return conv


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_clean_message_passes_filter_unchanged(
    db_session: AsyncSession,
    sample_client_user: User,
    user_conversation: Conversation,
):
    """A plain message with no contact info → stored as-is, no filter outcome."""
    svc = MessageService(db_session)
    clean_text = "Hello, I love your portfolio! Can you tell me more about your process?"

    message, outcome = await svc.send_message(
        sample_client_user,
        user_conversation.id,
        MessageCreate(content=clean_text),
    )

    # Filter either returned None or a zero-violation outcome
    if outcome is not None:
        assert outcome.total_violations == 0

    # Content preserved (no masking applied)
    assert message.content == clean_text
    assert str(message.sender_id) == str(sample_client_user.id)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_message_with_email_triggers_filter(
    db_session: AsyncSession,
    sample_client_user: User,
    user_conversation: Conversation,
):
    """A message containing an email address → filter fires, content is masked."""
    svc = MessageService(db_session)
    offending = "Contact me directly at client@example.com, it's faster than here."

    message, outcome = await svc.send_message(
        sample_client_user,
        user_conversation.id,
        MessageCreate(content=offending),
    )

    # Filter must have returned a non-None outcome
    assert outcome is not None
    assert outcome.total_violations >= 1

    # Stored content should NOT include the original email literal.
    # Exact masking placeholder depends on filter implementation — we
    # just assert the raw email string was scrubbed.
    assert "client@example.com" not in message.content

    # User's chat_violations counter was bumped on the DB.
    await db_session.refresh(sample_client_user)
    assert sample_client_user.chat_violations >= 1
