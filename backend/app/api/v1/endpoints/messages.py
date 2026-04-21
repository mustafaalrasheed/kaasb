"""
Kaasb Platform - Message Endpoints
"""

import uuid

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.message import Conversation
from app.models.user import User
from app.schemas.message import (
    ConversationCreate,
    ConversationJobInfo,
    ConversationListResponse,
    ConversationOrderInfo,
    ConversationSummary,
    MessageCreate,
    MessageDetail,
    MessageListResponse,
    MessageUserInfo,
    PresenceInfo,
    PresenceListResponse,
)
from app.services.message_service import MessageService
from app.services.presence import get_online

# Cap presence batch size — callers should only ask about users they can see
# (conversation partners), so this is a soft DoS guard.
_PRESENCE_BATCH_MAX = 100


def _serialize_conversation(
    c: Conversation, current_user_id: uuid.UUID,
) -> ConversationSummary:
    if current_user_id == c.participant_one_id:
        other = c.participant_two
        unread = c.unread_one
    else:
        other = c.participant_one
        unread = c.unread_two

    return ConversationSummary(
        id=c.id,
        conversation_type=c.conversation_type,
        other_user=MessageUserInfo(
            id=other.id,
            username=other.username,
            first_name=other.first_name,
            last_name=other.last_name,
            avatar_url=other.avatar_url,
        ),
        job=ConversationJobInfo(id=c.job.id, title=c.job.title) if c.job else None,
        order=ConversationOrderInfo(id=c.order.id, status=c.order.status.value) if c.order else None,
        last_message_text=c.last_message_text,
        last_message_at=c.last_message_at,
        message_count=c.message_count,
        unread_count=unread,
        created_at=c.created_at,
    )

router = APIRouter(prefix="/messages", tags=["Messages"])


# === Conversations ===

@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations",
)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all conversations for the current user."""
    service = MessageService(db)
    result = await service.get_conversations(current_user, page, page_size)

    conversations = [
        _serialize_conversation(c, current_user.id) for c in result["conversations"]
    ]

    return ConversationListResponse(
        conversations=conversations,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.post(
    "/conversations",
    response_model=ConversationSummary,
    summary="Start conversation",
    status_code=201,
)
async def start_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new conversation with another user."""
    service = MessageService(db)
    c = await service.start_conversation(current_user, data)
    return _serialize_conversation(c, current_user.id)


# === Messages ===

@router.get(
    "/conversations/{conversation_id}",
    response_model=MessageListResponse,
    summary="Get messages",
)
async def get_messages(
    conversation_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages in a conversation. Auto-marks as read."""
    service = MessageService(db)
    return await service.get_messages(current_user, conversation_id, page, page_size)


@router.post(
    "/support",
    response_model=ConversationSummary,
    summary="Contact support",
    status_code=201,
)
async def contact_support(
    message: str = Body(..., min_length=1, max_length=5000, embed=True,
                        description="First message to the support team"),
    order_id: uuid.UUID | None = Body(None, embed=True,
                                      description="Related order ID (optional context)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start or resume a support thread with the platform's admin team.
    Any user can call this — no admin ID required. If a support thread
    for this user already exists it is reused.
    """
    service = MessageService(db)
    c = await service.contact_support(current_user, message, order_id)
    return _serialize_conversation(c, current_user.id)


@router.post(
    "/conversations/{conversation_id}",
    response_model=MessageDetail,
    summary="Send message",
    status_code=201,
)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message in an existing conversation."""
    service = MessageService(db)
    msg, warning = await service.send_message(current_user, conversation_id, data)
    detail = MessageDetail.model_validate(msg)
    if warning is not None:
        detail.chat_warning_code = warning.code
        detail.chat_violation_count = warning.total_violations
    return detail


# === Presence ===

@router.get(
    "/presence",
    response_model=PresenceListResponse,
    summary="Batch presence lookup",
)
async def presence(
    user_ids: list[uuid.UUID] = Query(..., alias="user_ids"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch online/last-seen lookup. Clients call this when rendering the
    conversation list to show the green dot + "Last seen" subtitle.

    No authorization check on which users you can query — presence is
    low-stakes info that's already implicitly exposed by "message me" flows.
    """
    ids = user_ids[:_PRESENCE_BATCH_MAX]
    online = await get_online(ids)

    # Fetch last_seen_at for offline users only — online ones are online now.
    offline_ids = [u for u in ids if u not in online]
    last_seen_map: dict[uuid.UUID, object] = {}
    if offline_ids:
        rows = await db.execute(
            select(User.id, User.last_seen_at).where(User.id.in_(offline_ids))
        )
        last_seen_map = {row.id: row.last_seen_at for row in rows}

    return PresenceListResponse(
        users=[
            PresenceInfo(
                user_id=uid,
                is_online=uid in online,
                last_seen_at=last_seen_map.get(uid),  # type: ignore[arg-type]
            )
            for uid in ids
        ]
    )
