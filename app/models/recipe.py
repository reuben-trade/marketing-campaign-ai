"""Recipe model for storing structural templates extracted from ads."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Recipe(Base):
    """Recipes table - stores structural templates extracted from high-performing ads."""

    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Source ad reference
    source_ad_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ads.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Recipe metadata
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    total_duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Structure (array of beat definitions)
    structure: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Each beat: {beat_type, duration_range, characteristics, purpose}

    # Style attributes
    pacing: Mapped[str | None] = mapped_column(String(50))
    style: Mapped[str | None] = mapped_column(String(50))

    # Quality score (inherited from source ad)
    composite_score: Mapped[float | None] = mapped_column(Float)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    source_ad: Mapped["Ad | None"] = relationship(  # noqa: F821
        "Ad",
        foreign_keys=[source_ad_id],
        lazy="selectin",
    )
    visual_scripts: Mapped[list["VisualScript"]] = relationship(  # noqa: F821
        "VisualScript",
        back_populates="recipe",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_recipes_source_ad_id", "source_ad_id"),
        Index("idx_recipes_composite_score", "composite_score"),
        Index("idx_recipes_style", "style"),
        Index("idx_recipes_pacing", "pacing"),
        Index("idx_recipes_created_at", "created_at"),
    )

    # Valid pacing types
    PACING_TYPES = [
        "fast",
        "medium",
        "slow",
        "dynamic",
    ]

    # Valid style types
    STYLE_TYPES = [
        "ugc",
        "polished",
        "cinematic",
        "talking_head",
        "demo",
        "testimonial",
        "animation",
    ]
