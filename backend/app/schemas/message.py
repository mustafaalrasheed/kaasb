"""
Kaasb Platform - Message Schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.message import ConversationType, SenderRole

# Attachment MIME allowlist — covers images (inline preview), PDFs, and common
# office docs. Everything else (executables, archives, scripts) is rejected to
# shrink the phishing / malware delivery surface on chat.
_ALLOWED_ATTACHMENT_MIMES = frozenset({
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv",
})
_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB per attachment


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
    """File attached to a message (image, document, …).

    URL must be a relative path produced by our own upload endpoint
    (``/uploads/...``) — external URLs are rejected to prevent the chat from
    being used as a phishing/malware delivery vector.
    """
    url: str = Field(min_length=1, max_length=500)
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=3, max_length=100)
    size_bytes: int = Field(ge=0, le=_MAX_ATTACHMENT_BYTES)

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        # Accept only paths produced by our own upload endpoint. Reject absolute
        # URLs, protocol-relative URLs, and path traversal.
        if not v.startswith("/uploads/"):
            raise ValueError("Attachment URL must be a /uploads/ path")
        if ".." in v:
            raise ValueError("Attachment URL contains a path traversal sequence")
        return v

    @field_validator("mime_type")
    @classmethod
    def _validate_mime(cls, v: str) -> str:
        if v not in _ALLOWED_ATTACHMENT_MIMES:
            raise ValueError(f"Attachment type '{v}' is not allowed")
        return v

    @field_validator("filename")
    @classmethod
    def _validate_filename(cls, v: str) -> str:
        if "/" in v or "\\" in v or ".." in v:
            raise ValueError("Invalid filename")
        return v


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

    # Populated only in the response to the sender when their first off-platform
    # violation masked the message. The UI uses this to surface a warning toast.
    chat_warning_code: str | None = None
    chat_violation_count: int | None = None

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
