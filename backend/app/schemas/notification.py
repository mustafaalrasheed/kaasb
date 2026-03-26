"""
Kaasb Platform - Notification Schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationDetail(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool
    link_type: str | None = None
    link_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationDetail]
    total: int
    unread_count: int
    page: int
    page_size: int
    total_pages: int


class NotificationMarkRead(BaseModel):
    """Mark specific notifications as read."""
    notification_ids: list[uuid.UUID]


class UnreadCount(BaseModel):
    count: int
