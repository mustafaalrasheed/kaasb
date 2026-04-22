"""
Kaasb Platform - Message Schemas
"""

import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
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


# Attachment policy: only these MIME types are accepted from the client.
# Kept narrow on purpose — chat attachments are images + documents + a few
# common formats for Iraqi freelance workflows. Expand intentionally when a
# new use case lands; a wide whitelist is the main stored-XSS vector here
# because the frontend renders the URL.
_ALLOWED_ATTACHMENT_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/zip",
    "text/plain",
})


class MessageAttachment(BaseModel):
    """File attached to a message (image, document, …)."""
    url: str
    filename: str
    mime_type: str
    size_bytes: int = Field(ge=0)

    @field_validator("url")
    @classmethod
    def _validate_url_scheme(cls, v: str) -> str:
        """Reject any URL whose scheme is not http(s). Blocks data:,
        javascript:, file:, and schemeless payloads — the usual stored-XSS
        vectors when the frontend renders attachment links."""
        parsed = urlparse(v.strip())
        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("attachment url must use http or https scheme")
        if not parsed.netloc:
            raise ValueError("attachment url must have a host")
        return v.strip()

    @field_validator("mime_type")
    @classmethod
    def _validate_mime(cls, v: str) -> str:
        """Whitelist-only MIME types. An unfamiliar mime arrives via the
        frontend's upload path; anything outside the allowlist likely means
        a crafted payload or a filter-bypass attempt."""
        normalised = v.strip().lower()
        if normalised not in _ALLOWED_ATTACHMENT_MIME_TYPES:
            raise ValueError(
                f"mime_type '{v}' is not allowed for chat attachments"
            )
        return normalised

    @field_validator("size_bytes")
    @classmethod
    def _validate_size(cls, v: int) -> int:
        """Clamp to the same MAX_UPLOAD_SIZE_MB limit used by avatar/gig
        upload paths. A claimed size above that bound is rejected up front —
        the actual file bytes are validated separately by the upload
        endpoint once that lands."""
        limit = get_settings().MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if v > limit:
            raise ValueError(
                f"attachment size {v} exceeds MAX_UPLOAD_SIZE_MB limit ({limit} bytes)"
            )
        return v

    @field_validator("filename")
    @classmethod
    def _validate_filename(cls, v: str) -> str:
        """Reject path-traversal sequences. The upload path saves files under
        a content-hashed name anyway, but a crafted filename could leak to
        logs or UI contexts; keeping it clean is cheap."""
        v = v.strip()
        if not v:
            raise ValueError("filename required")
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("filename must not contain path separators")
        if len(v) > 255:
            raise ValueError("filename too long (max 255 chars)")
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
