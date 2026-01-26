"""Rendered video model for tracking video rendering jobs."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class RenderedVideo(Base):
    """Rendered videos table - tracks video rendering jobs and outputs."""

    __tablename__ = "rendered_videos"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Project reference
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Remotion composition
    composition_id: Mapped[str | None] = mapped_column(String(100))

    # Payload sent to Remotion
    remotion_payload: Mapped[dict | None] = mapped_column(JSONB)

    # Render status: pending, rendering, completed, failed
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Output
    video_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)

    # Video metadata
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)

    # Render performance
    render_time_seconds: Mapped[float | None] = mapped_column(Float)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project",
        back_populates="rendered_videos",
    )

    __table_args__ = (
        Index("idx_rendered_videos_project_id", "project_id"),
        Index("idx_rendered_videos_status", "status"),
        Index("idx_rendered_videos_created_at", "created_at"),
    )

    # Valid status values
    STATUS_PENDING = "pending"
    STATUS_RENDERING = "rendering"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    VALID_STATUSES = [
        STATUS_PENDING,
        STATUS_RENDERING,
        STATUS_COMPLETED,
        STATUS_FAILED,
    ]
