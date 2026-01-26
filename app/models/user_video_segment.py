"""User video segment model for storing analyzed segments from user uploads."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class UserVideoSegment(Base):
    """User video segments table - stores segments extracted from user uploads."""

    __tablename__ = "user_video_segments"

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

    # Source file info
    source_file_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_file_name: Mapped[str | None] = mapped_column(String(500))
    source_file_url: Mapped[str | None] = mapped_column(Text)

    # Timing (in seconds)
    timestamp_start: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp_end: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Analysis results
    visual_description: Mapped[str | None] = mapped_column(Text)
    action_tags: Mapped[dict | None] = mapped_column(JSONB)

    # Embedding for semantic search
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))

    # Thumbnail
    thumbnail_url: Mapped[str | None] = mapped_column(Text)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project",
        back_populates="video_segments",
    )

    __table_args__ = (
        Index("idx_user_video_segments_project_id", "project_id"),
        Index("idx_user_video_segments_source_file_id", "source_file_id"),
        Index("idx_user_video_segments_created_at", "created_at"),
        # HNSW index for embeddings is created in migration
    )
