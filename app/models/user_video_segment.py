"""User video segment model for storing analyzed segments from user uploads."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB  # Still needed for action_tags, keywords
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

    # =========================================================================
    # Clip Ordering Fields (Doubly-Linked List) - Sprint 5 s5-t6
    # =========================================================================
    previous_segment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("user_video_segments.id", ondelete="SET NULL"),
        nullable=True,
    )
    next_segment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("user_video_segments.id", ondelete="SET NULL"),
        nullable=True,
    )
    segment_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_segments_in_source: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # =========================================================================
    # Transcript Fields - Sprint 5 s5-t5
    # Transcript text and speaker label populated by post-processing task from global SRT
    # =========================================================================
    transcript_text: Mapped[str | None] = mapped_column(Text)
    speaker_label: Mapped[str | None] = mapped_column(String(20))

    # =========================================================================
    # V2 Analysis Fields - Sprint 5 s5-t7
    # =========================================================================
    # Section classification (predefined list + other)
    section_type: Mapped[str | None] = mapped_column(String(30))
    # Descriptive label (always populated, e.g., "BMX halfpipe trick")
    section_label: Mapped[str | None] = mapped_column(String(200))
    attention_score: Mapped[int | None] = mapped_column(Integer)  # 1-10
    emotion_intensity: Mapped[int | None] = mapped_column(Integer)  # 1-10
    color_grading: Mapped[str | None] = mapped_column(String(30))
    lighting_style: Mapped[str | None] = mapped_column(String(30))
    has_speech: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Topic keywords + persuasive words (e.g., ["BMX", "trick", "outdoor", "guaranteed"])
    keywords: Mapped[list | None] = mapped_column(JSONB)
    # Rich narrative breakdown with embedded timestamps for Director agent decisions
    # NOTE: Can add parsing later if we need structured format - timestamps must be accurate
    detailed_breakdown: Mapped[str | None] = mapped_column(Text)

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

    # Self-referential relationships for clip ordering
    previous_segment: Mapped["UserVideoSegment | None"] = relationship(
        "UserVideoSegment",
        foreign_keys=[previous_segment_id],
        remote_side="UserVideoSegment.id",
        uselist=False,
    )
    next_segment: Mapped["UserVideoSegment | None"] = relationship(
        "UserVideoSegment",
        foreign_keys=[next_segment_id],
        remote_side="UserVideoSegment.id",
        uselist=False,
    )

    __table_args__ = (
        Index("idx_user_video_segments_project_id", "project_id"),
        Index("idx_user_video_segments_source_file_id", "source_file_id"),
        Index("idx_user_video_segments_created_at", "created_at"),
        Index("idx_segments_ordering", "source_file_id", "segment_index"),
        # HNSW index for embeddings is created in migration
    )
