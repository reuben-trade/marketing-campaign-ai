"""Notification model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class NotificationType(str, Enum):
    """Notification types."""

    NEW_ADS = "new_ads"
    ANALYSIS_COMPLETE = "analysis_complete"
    RECOMMENDATION_READY = "recommendation_ready"
    COMPETITOR_DISCOVERED = "competitor_discovered"
    SYSTEM = "system"


class Notification(Base):
    """Notifications table for user alerts."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional references
    competitor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("competitors.id", ondelete="SET NULL"),
        nullable=True,
    )
    ad_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ads.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Metadata
    ad_count: Mapped[int | None] = mapped_column(nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    competitor: Mapped["Competitor | None"] = relationship(  # noqa: F821
        "Competitor",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_notifications_created_at", "created_at"),
        Index("idx_notifications_read_at", "read_at"),
        Index("idx_notifications_type", "type"),
    )

    @property
    def is_read(self) -> bool:
        """Check if notification has been read."""
        return self.read_at is not None
