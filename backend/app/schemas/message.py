"""
Kaasb Platform - Message Schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.message import ConversationType, SenderRole


class MessageUserInfo(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class ConversationJobInfo(BaseModel):
    id: uuid.UUID
    title: str

    model_config = {"from_attributes": True}


class ConversationOrderInfo(BaseModel):
    id: uuid.UUID
    status: str

    model_config = {"from_attributes": True}


class MessageAttachment(BaseModel):
    """File attached to a message (image, document, …)."""
    url: str
    filename: str
    mime_type: str
    size_bytes: int = Field(ge=0)


class ConversationCreate(BaseModel):
    """Start a new conversation."""
    recipient_id: uuid.UUID
    job_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    initial_message: str = Field(min_length=1, max_length=5000)


class ConversationSummary(BaseModel):
    id: uuid.UUID
    conversation_type: ConversationType
    other_user: MessageUserInfo
    job: ConversationJobInfo | None = None
    order: ConversationOrderInfo | None = None
    last_message_text: str | None = None
    last_message_at: datetime | None = None
    message_count: int = 0
    unread_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageCreate(BaseModel):
    """Send a message in a conversation."""
    content: str = Field(min_length=1, max_length=5000)
    attachments: list[MessageAttachment] = Field(default_factory=list, max_length=10)


class MessageDetail(BaseModel):
    id: uuid.UUID
    content: str
    is_read: bool
    read_at: datetime | None = None
    is_system: bool
    sender: MessageUserInfo
    sender_role: SenderRole
    attachments: list[MessageAttachment] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class PresenceInfo(BaseModel):
    """Online/last-seen status for a single user."""
    user_id: uuid.UUID
    is_online: bool
    last_seen_at: datetime | None = None


class PresenceListResponse(BaseModel):
    users: list[PresenceInfo]


class MessageListResponse(BaseModel):
    messages: list[MessageDetail]
    total: int
    page: int
    page_size: int
    total_pages: int
