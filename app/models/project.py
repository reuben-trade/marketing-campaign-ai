"""Project model for organizing user ad creation projects."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Project(Base):
    """Projects table - organizes user raw footage into ad creation projects."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Project metadata
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("brand_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status: draft, processing, ready, rendered
    status: Mapped[str] = mapped_column(String(50), default="draft")

    # Inspiration ads (array of ad IDs)
    inspiration_ads: Mapped[dict | None] = mapped_column(JSONB)

    # User prompt for generation
    user_prompt: Mapped[str | None] = mapped_column(Text)

    # Upload constraints
    max_videos: Mapped[int] = mapped_column(Integer, default=10)
    max_total_size_mb: Mapped[int] = mapped_column(Integer, default=500)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    brand_profile: Mapped["BrandProfile | None"] = relationship(  # noqa: F821
        "BrandProfile",
        back_populates="projects",
        lazy="selectin",
    )
    video_segments: Mapped[list["UserVideoSegment"]] = relationship(  # noqa: F821
        "UserVideoSegment",
        back_populates="project",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    visual_scripts: Mapped[list["VisualScript"]] = relationship(  # noqa: F821
        "VisualScript",
        back_populates="project",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    rendered_videos: Mapped[list["RenderedVideo"]] = relationship(  # noqa: F821
        "RenderedVideo",
        back_populates="project",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_projects_brand_profile_id", "brand_profile_id"),
        Index("idx_projects_status", "status"),
        Index("idx_projects_created_at", "created_at"),
    )

    # Valid status values
    STATUS_DRAFT = "draft"
    STATUS_PROCESSING = "processing"
    STATUS_READY = "ready"
    STATUS_RENDERED = "rendered"

    VALID_STATUSES = [
        STATUS_DRAFT,
        STATUS_PROCESSING,
        STATUS_READY,
        STATUS_RENDERED,
    ]
