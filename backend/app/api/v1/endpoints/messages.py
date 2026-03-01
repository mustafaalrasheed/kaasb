"""
Kaasb Platform - Message Endpoints
"""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.message_service import MessageService
from app.schemas.message import (
    ConversationCreate, ConversationSummary, ConversationListResponse,
    MessageCreate, MessageDetail, MessageListResponse,
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

    # Serialize conversations with other_user enrichment
    conversations = []
    for c in result["conversations"]:
        other = c._other_user
        conversations.append(
            ConversationSummary(
                id=c.id,
                other_user={
                    "id": other.id,
                    "username": other.username,
                    "first_name": other.first_name,
                    "last_name": other.last_name,
                    "avatar_url": other.avatar_url,
                },
                job={"id": c.job.id, "title": c.job.title} if c.job else None,
                last_message_text=c.last_message_text,
                last_message_at=c.last_message_at,
                message_count=c.message_count,
                unread_count=c._unread_count,
                created_at=c.created_at,
            )
        )

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

    # Determine other user
    if current_user.id == c.participant_one_id:
        other = c.participant_two
        unread = c.unread_one
    else:
        other = c.participant_one
        unread = c.unread_two

    return ConversationSummary(
        id=c.id,
        other_user={
            "id": other.id,
            "username": other.username,
            "first_name": other.first_name,
            "last_name": other.last_name,
            "avatar_url": other.avatar_url,
        },
        job={"id": c.job.id, "title": c.job.title} if c.job else None,
        last_message_text=c.last_message_text,
        last_message_at=c.last_message_at,
        message_count=c.message_count,
        unread_count=unread,
        created_at=c.created_at,
    )


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
    return await service.send_message(current_user, conversation_id, data)
