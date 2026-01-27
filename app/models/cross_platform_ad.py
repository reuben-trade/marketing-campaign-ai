"""Cross-platform ad model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class CrossPlatformAd(Base):
    """Cross-platform ads table - tracks ads across Facebook, TikTok, Google."""

    __tablename__ = "cross_platform_ads"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # Advertiser identification
    domain: Mapped[str] = mapped_column(String(255), nullable=False)

    # Platform details
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    # Values: "facebook", "tiktok", "google"
    platform_ad_id: Mapped[str | None] = mapped_column(String(255))
    platform_ad_url: Mapped[str | None] = mapped_column(Text)

    # Creative matching
    creative_hash: Mapped[str | None] = mapped_column(String(64))  # Perceptual hash

    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")
    # Values: "active", "inactive"
    is_universal_winner: Mapped[bool] = mapped_column(Boolean, default=False)
    # True if found on 3+ platforms

    # Link to our ads table (for Facebook ads)
    ad_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ads.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    ad: Mapped["Ad | None"] = relationship(  # noqa: F821
        "Ad",
        back_populates="cross_platform_entries",
    )

    __table_args__ = (
        Index("idx_cross_platform_ads_domain", "domain"),
        Index("idx_cross_platform_ads_platform", "platform"),
        Index("idx_cross_platform_ads_creative_hash", "creative_hash"),
        Index("idx_cross_platform_ads_universal_winner", "is_universal_winner"),
    )

    # Valid platforms
    PLATFORMS = ["facebook", "tiktok", "google"]

    @property
    def is_active(self) -> bool:
        """Check if the ad is currently active."""
        return self.status == "active"
