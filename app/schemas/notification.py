"""Notification schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Notification types."""

    NEW_ADS = "new_ads"
    ANALYSIS_COMPLETE = "analysis_complete"
    RECOMMENDATION_READY = "recommendation_ready"
    COMPETITOR_DISCOVERED = "competitor_discovered"
    SYSTEM = "system"


class NotificationBase(BaseModel):
    """Base notification schema."""

    type: NotificationType
    title: str = Field(..., max_length=255)
    message: str
    competitor_id: UUID | None = None
    ad_id: UUID | None = None
    ad_count: int | None = None


class NotificationCreate(NotificationBase):
    """Create notification schema."""

    pass


class NotificationResponse(NotificationBase):
    """Notification response schema."""

    id: UUID
    created_at: datetime
    read_at: datetime | None = None
    is_read: bool = False

    # Optional nested data
    competitor_name: str | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class NotificationListResponse(BaseModel):
    """List of notifications response."""

    items: list[NotificationResponse]
    total: int
    unread_count: int


class NotificationMarkReadRequest(BaseModel):
    """Request to mark notifications as read."""

    notification_ids: list[UUID] | None = None  # If None, mark all as read
