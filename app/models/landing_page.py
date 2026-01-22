"""Landing page model."""

import hashlib
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class LandingPage(Base):
    """Landing pages table - stores scraped landing page data."""

    __tablename__ = "landing_pages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )

    # URL identification
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    final_url: Mapped[str | None] = mapped_column(Text)  # URL after redirects

    # Page content
    page_title: Mapped[str | None] = mapped_column(Text)
    meta_description: Mapped[str | None] = mapped_column(Text)
    meta_keywords: Mapped[str | None] = mapped_column(Text)
    headings: Mapped[dict | None] = mapped_column(JSON)  # {h1: [], h2: [], h3: []}
    content_preview: Mapped[str | None] = mapped_column(Text)  # First ~500 chars
    cta_buttons: Mapped[list | None] = mapped_column(JSON)  # [{text: "", href: ""}]

    # Technical metrics
    http_status_code: Mapped[int | None] = mapped_column(Integer)
    load_time_ms: Mapped[int | None] = mapped_column(Integer)

    # Screenshots (Supabase storage paths)
    desktop_screenshot_path: Mapped[str | None] = mapped_column(Text)
    mobile_screenshot_path: Mapped[str | None] = mapped_column(Text)

    # Tracking pixel detection
    meta_pixel_id: Mapped[str | None] = mapped_column(String(50))
    has_capi: Mapped[bool] = mapped_column(Boolean, default=False)
    google_ads_tag_id: Mapped[str | None] = mapped_column(String(50))
    tiktok_pixel_id: Mapped[str | None] = mapped_column(String(50))
    technical_sophistication_score: Mapped[int | None] = mapped_column(Integer)  # 0-100

    # Timestamps
    first_scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    scrape_count: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    ads: Mapped[list["Ad"]] = relationship(  # noqa: F821
        "Ad",
        back_populates="landing_page",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_landing_pages_url_hash", "url_hash"),
        Index("idx_landing_pages_meta_pixel_id", "meta_pixel_id"),
    )

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """Generate a SHA256 hash of the URL for fast lookups."""
        return hashlib.sha256(url.encode()).hexdigest()

    @property
    def has_tracking(self) -> bool:
        """Check if any tracking pixels are detected."""
        return bool(self.meta_pixel_id or self.google_ads_tag_id or self.tiktok_pixel_id)

    def calculate_sophistication_score(self) -> int:
        """Calculate technical sophistication score based on tracking setup."""
        score = 0
        if self.meta_pixel_id:
            score += 20
        if self.has_capi:
            score += 30
        if self.google_ads_tag_id:
            score += 20
        if self.tiktok_pixel_id:
            score += 20
        if self.load_time_ms and self.load_time_ms < 3000:
            score += 10
        return min(score, 100)
