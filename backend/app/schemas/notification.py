"""
Kaasb Platform - Notification Schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.notification import NotificationType


class NotificationDetail(BaseModel):
    id: uuid.UUID
    # Typed against the enum so the API surfaces the exact set of values the
    # frontend can render, and so a typo in a new service-layer emission
    # (e.g. NotificationType.FOO) fails fast at serialization time instead
    # of silently reaching the bell.
    type: NotificationType
    title: str
    message: str
    is_read: bool
    link_type: str | None = None
    link_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "use_enum_values": True}


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
