"""
Kaasb Platform - Message Schemas
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MessageUserInfo(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class ConversationJobInfo(BaseModel):
    id: uuid.UUID
    title: str

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    """Start a new conversation."""
    recipient_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    initial_message: str = Field(min_length=1, max_length=5000)


class ConversationSummary(BaseModel):
    id: uuid.UUID
    other_user: MessageUserInfo
    job: Optional[ConversationJobInfo] = None
    last_message_text: Optional[str] = None
    last_message_at: Optional[datetime] = None
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


class MessageDetail(BaseModel):
    id: uuid.UUID
    content: str
    is_read: bool
    sender: MessageUserInfo
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    messages: list[MessageDetail]
    total: int
    page: int
    page_size: int
    total_pages: int
