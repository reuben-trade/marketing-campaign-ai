"""Ad creative analysis model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AdCreativeAnalysis(Base):
    """Ad creative analysis table - stores AI-powered analysis of ad creatives."""

    __tablename__ = "ad_creative_analysis"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    ad_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ads.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Creative archetype classification
    creative_archetype: Mapped[str | None] = mapped_column(String(50))
    # Values: "UGC", "Problem/Solution Demo", "Lo-fi Meme", "High-Production Studio"
    archetype_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))  # 0.00-1.00

    # Hook/offer detection
    hook_offer_type: Mapped[str | None] = mapped_column(String(100))
    # Values: "Free Quote", "Percentage Discount", "BOGO", "Limited Time", etc.
    offer_details: Mapped[str | None] = mapped_column(Text)
    offer_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))

    # Emotional analysis
    primary_emotion: Mapped[str | None] = mapped_column(String(50))
    # Values: "urgency", "aspiration", "fear", "belonging", "curiosity"

    # Production quality
    production_quality_score: Mapped[int | None] = mapped_column(Integer)  # 1-10
    text_to_image_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # percentage

    # Visual analysis
    color_palette: Mapped[list | None] = mapped_column(JSON)  # ["#FF5733", "#C70039"]
    has_human_face: Mapped[bool | None] = mapped_column(Boolean)
    has_product_shot: Mapped[bool | None] = mapped_column(Boolean)

    # Metadata
    analysis_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    model_used: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    ad: Mapped["Ad"] = relationship(  # noqa: F821
        "Ad",
        back_populates="creative_analysis",
    )

    __table_args__ = (
        Index("idx_ad_creative_analysis_ad_id", "ad_id"),
        Index("idx_ad_creative_analysis_archetype", "creative_archetype"),
        Index("idx_ad_creative_analysis_hook_offer", "hook_offer_type"),
    )

    # Valid archetype values
    ARCHETYPES = [
        "UGC",
        "Problem/Solution Demo",
        "Lo-fi Meme",
        "High-Production Studio",
    ]

    # Valid emotion values
    EMOTIONS = [
        "urgency",
        "aspiration",
        "fear",
        "belonging",
        "curiosity",
    ]

    # Valid hook/offer types
    OFFER_TYPES = [
        "Free Quote/Consultation",
        "Percentage Discount",
        "Dollar Amount Off",
        "BOGO",
        "Free Shipping",
        "Free Trial",
        "Payment Plan",
        "Bundle Deal",
        "Seasonal Sale",
        "Limited Time Offer",
        "New Product Launch",
        "Problem Awareness",
        "No Offer",
        "Other",
    ]
