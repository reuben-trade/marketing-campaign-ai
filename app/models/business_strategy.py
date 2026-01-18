"""Business Strategy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class BusinessStrategy(Base):
    """Target business strategy table."""

    __tablename__ = "business_strategy"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_description: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(255))

    # JSONB fields for complex nested data
    target_audience: Mapped[dict | None] = mapped_column(JSONB)
    # Structure: {
    #   "demographics": str,
    #   "psychographics": str,
    #   "pain_points": list[str]
    # }

    brand_voice: Mapped[dict | None] = mapped_column(JSONB)
    # Structure: {
    #   "tone": str,
    #   "personality_traits": list[str],
    #   "messaging_guidelines": str
    # }

    market_position: Mapped[str | None] = mapped_column(String(50))
    # e.g., "challenger", "leader", "niche"

    price_point: Mapped[str | None] = mapped_column(String(50))
    # e.g., "premium", "mid-market", "budget"

    business_life_stage: Mapped[str | None] = mapped_column(String(50))
    # e.g., "startup", "growth", "mature"

    unique_selling_points: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    competitive_advantages: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    marketing_objectives: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    raw_pdf_url: Mapped[str | None] = mapped_column(Text)

    extracted_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
