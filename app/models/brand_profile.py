"""Brand profile model for storing user brand context."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class BrandProfile(Base):
    """Brand profiles table - stores brand context for ad generation."""

    __tablename__ = "brand_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Industry and niche
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    niche: Mapped[str | None] = mapped_column(String(200))
    core_offer: Mapped[str | None] = mapped_column(Text)

    # Competitors (array of competitor IDs)
    competitors: Mapped[dict | None] = mapped_column(JSONB)

    # Brand voice
    keywords: Mapped[dict | None] = mapped_column(JSONB)
    tone: Mapped[str | None] = mapped_column(String(50))
    forbidden_terms: Mapped[dict | None] = mapped_column(JSONB)

    # Visual identity
    logo_url: Mapped[str | None] = mapped_column(Text)
    primary_color: Mapped[str | None] = mapped_column(String(7))
    font_family: Mapped[str | None] = mapped_column(String(100))

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
    projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        "Project",
        back_populates="brand_profile",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_brand_profiles_industry", "industry"),
        Index("idx_brand_profiles_created_at", "created_at"),
    )
