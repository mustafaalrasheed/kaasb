"""
Kaasb Platform - Message Endpoints
"""

import uuid

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import or_, select
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
    """Send a message in an existing conversation.

    Application-level rate limit: 20 messages per 60 seconds per
    (user, conversation). The platform-wide per-IP limiter in
    middleware/security.py still applies; this adds a narrower guard on
    the abuse path where a single user floods a single thread.
    """
    from app.core.exceptions import RateLimitError  # noqa: PLC0415
    from app.middleware.monitoring import RATE_LIMIT_HITS  # noqa: PLC0415
    from app.middleware.security import rate_limiter  # noqa: PLC0415

    rate_key = f"msg_send:{current_user.id}:{conversation_id}"
    if not await rate_limiter.is_allowed(rate_key, limit=20, window=60):
        RATE_LIMIT_HITS.labels(tier="message_send").inc()
        raise RateLimitError(
            "You're sending messages too fast — slow down for a moment."
        )

    service = MessageService(db)
    return await service.send_message(current_user, conversation_id, data)


# === Presence ===

@router.get(
    "/presence",
    response_model=PresenceListResponse,
    summary="Batch presence lookup (scoped to conversation partners)",
)
async def presence(
    user_ids: list[uuid.UUID] = Query(..., alias="user_ids"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch online/last-seen lookup, scoped to users the caller already has
    a conversation with. Clients call this when rendering the conversation
    list to show the green dot + "Last seen" subtitle.

    Scope: only users who share at least one conversation with the caller
    (as the other participant) are returned. Queried IDs for strangers are
    silently dropped — the response says nothing about whether those users
    exist or are online. Staff (admin/support) are exempt from the scope
    check so their inbox listing can show user presence without needing a
    prior conversation row.
    """
    ids = user_ids[:_PRESENCE_BATCH_MAX]

    # Staff skip the scope check: they legitimately need presence for any
    # user they're managing in the admin dashboard.
    is_staff = bool(getattr(current_user, "is_superuser", False) or
                    getattr(current_user, "is_support", False))
    if not is_staff and ids:
        # Find the subset of requested IDs that share a conversation with
        # the caller. A single SELECT with OR on participant_one/two
        # handles either slot.
        partners_stmt = (
            select(Conversation.participant_one_id, Conversation.participant_two_id)
            .where(
                or_(
                    Conversation.participant_one_id == current_user.id,
                    Conversation.participant_two_id == current_user.id,
                )
            )
        )
        rows = await db.execute(partners_stmt)
        allowed: set[uuid.UUID] = set()
        for p1, p2 in rows.all():
            if p1 != current_user.id:
                allowed.add(p1)
            if p2 != current_user.id:
                allowed.add(p2)
        ids = [u for u in ids if u in allowed]

    online = await get_online(ids)

    # Fetch last_seen_at for offline users only — online ones are online now.
    offline_ids = [u for u in ids if u not in online]
    last_seen_map: dict[uuid.UUID, object] = {}
    if offline_ids:
        rows2 = await db.execute(
            select(User.id, User.last_seen_at).where(User.id.in_(offline_ids))
        )
        last_seen_map = {row.id: row.last_seen_at for row in rows2}

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
