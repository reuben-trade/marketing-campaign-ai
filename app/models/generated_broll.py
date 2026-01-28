"""Generated B-Roll models for tracking Veo 2 video generation."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class GeneratedBRoll(Base):
    """Generated B-Roll table - tracks Veo 2 video generation jobs."""

    __tablename__ = "generated_broll"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Generation parameters
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(10), nullable=False)  # "9:16", "16:9", "1:1"
    style: Mapped[str] = mapped_column(String(50), nullable=False)  # realistic, cinematic, etc.
    num_variants: Mapped[int] = mapped_column(Integer, default=2)
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    seed: Mapped[int | None] = mapped_column(Integer)

    # Optional project/slot association
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    slot_id: Mapped[str | None] = mapped_column(String(100))  # Visual script slot ID

    # Status: pending, processing, completed, failed
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generation_time_seconds: Mapped[float | None] = mapped_column(Float)

    # Relationships
    clips: Mapped[list["GeneratedBRollClip"]] = relationship(
        "GeneratedBRollClip",
        back_populates="generation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_generated_broll_project_id", "project_id"),
        Index("idx_generated_broll_status", "status"),
        Index("idx_generated_broll_created_at", "created_at"),
        Index("idx_generated_broll_slot_id", "slot_id"),
    )


class GeneratedBRollClip(Base):
    """Generated B-Roll clips - individual video variants from a generation job."""

    __tablename__ = "generated_broll_clips"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Parent generation
    generation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("generated_broll.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Video metadata
    url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)

    # Variant index (0-based)
    variant_index: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    generation: Mapped["GeneratedBRoll"] = relationship(
        "GeneratedBRoll",
        back_populates="clips",
    )

    __table_args__ = (Index("idx_generated_broll_clips_generation_id", "generation_id"),)
