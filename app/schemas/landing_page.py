"""Landing page schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HeadingsContent(BaseModel):
    """Headings extracted from landing page."""

    h1: list[str] = Field(default_factory=list)
    h2: list[str] = Field(default_factory=list)
    h3: list[str] = Field(default_factory=list)


class CTAButton(BaseModel):
    """Call-to-action button extracted from landing page."""

    text: str = Field(..., description="Button text")
    href: str | None = Field(None, description="Button destination URL")


class LandingPageBase(BaseModel):
    """Base schema for landing page."""

    url: str = Field(..., description="Landing page URL")
    final_url: str | None = Field(None, description="Final URL after redirects")
    page_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    headings: HeadingsContent | None = None
    content_preview: str | None = Field(None, description="First ~500 chars of content")
    cta_buttons: list[CTAButton] | None = None
    http_status_code: int | None = None
    load_time_ms: int | None = Field(None, ge=0)


class LandingPageCreate(LandingPageBase):
    """Schema for creating a landing page record."""

    url_hash: str = Field(..., description="SHA256 hash of URL")
    desktop_screenshot_path: str | None = None
    mobile_screenshot_path: str | None = None
    meta_pixel_id: str | None = None
    has_capi: bool = False
    google_ads_tag_id: str | None = None
    tiktok_pixel_id: str | None = None
    technical_sophistication_score: int | None = Field(None, ge=0, le=100)


class LandingPageResponse(LandingPageBase):
    """Schema for landing page response."""

    id: UUID
    url_hash: str
    desktop_screenshot_path: str | None = None
    mobile_screenshot_path: str | None = None
    meta_pixel_id: str | None = None
    has_capi: bool
    google_ads_tag_id: str | None = None
    tiktok_pixel_id: str | None = None
    technical_sophistication_score: int | None = None
    first_scraped_at: datetime
    last_updated_at: datetime
    scrape_count: int

    model_config = {"from_attributes": True}


class LandingPageSummary(BaseModel):
    """Brief summary for embedding in other responses."""

    id: UUID
    url: str
    page_title: str | None = None
    meta_pixel_id: str | None = None
    technical_sophistication_score: int | None = None

    model_config = {"from_attributes": True}


class TrackingPixelInfo(BaseModel):
    """Tracking pixel detection results."""

    meta_pixel_id: str | None = None
    has_capi: bool = False
    google_ads_tag_id: str | None = None
    tiktok_pixel_id: str | None = None
    technical_sophistication_score: int = Field(0, ge=0, le=100)


class LandingPageScrapeRequest(BaseModel):
    """Request to scrape a landing page."""

    url: str = Field(..., description="URL to scrape")
    force_refresh: bool = Field(False, description="Rescrape even if already exists")
    capture_screenshots: bool = Field(True, description="Capture desktop/mobile screenshots")
    detect_pixels: bool = Field(True, description="Detect tracking pixels")
