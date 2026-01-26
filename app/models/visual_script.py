"""Visual script model for storing generated ad scripts with slots."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class VisualScript(Base):
    """Visual scripts table - stores generated scripts with slot definitions."""

    __tablename__ = "visual_scripts"

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

    # Recipe reference (template used)
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Script content
    total_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    slots: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Each slot: {id, beat_type, target_duration, search_query, overlay_text, etc.}

    # Audio and pacing
    audio_suggestion: Mapped[str | None] = mapped_column(String(100))
    pacing_notes: Mapped[str | None] = mapped_column(Text)

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
    project: Mapped["Project"] = relationship(  # noqa: F821
        "Project",
        back_populates="visual_scripts",
    )
    recipe: Mapped["Recipe | None"] = relationship(  # noqa: F821
        "Recipe",
        back_populates="visual_scripts",
    )

    __table_args__ = (
        Index("idx_visual_scripts_project_id", "project_id"),
        Index("idx_visual_scripts_recipe_id", "recipe_id"),
        Index("idx_visual_scripts_created_at", "created_at"),
    )
