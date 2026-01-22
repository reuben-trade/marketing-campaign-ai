"""Competitor model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Competitor(Base):
    """Competitors table."""

    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    facebook_page: Mapped[str | None] = mapped_column(String(255), unique=True)
    # e.g., "GroutProAus" from facebook.com/GroutProAus
    industry: Mapped[str | None] = mapped_column(String(255))
    follower_count: Mapped[int | None] = mapped_column(Integer)
    is_market_leader: Mapped[bool] = mapped_column(Boolean, default=False)
    market_position: Mapped[str | None] = mapped_column(String(50))
    # e.g., "leader", "challenger", "niche"

    discovery_method: Mapped[str | None] = mapped_column(String(50))
    # e.g., "automated", "manual_add"

    discovered_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_retrieved: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    # Additional metadata about the competitor

    # Relationships
    ads: Mapped[list["Ad"]] = relationship(  # noqa: F821
        "Ad",
        back_populates="competitor",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_competitors_active", "active"),
        Index("idx_competitors_last_retrieved", "last_retrieved"),
    )
