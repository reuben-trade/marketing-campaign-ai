"""Cross-platform ad schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


Platform = Literal["facebook", "tiktok", "google"]
AdStatus = Literal["active", "inactive"]


class CrossPlatformAdBase(BaseModel):
    """Base schema for cross-platform ad."""

    domain: str = Field(..., description="Advertiser's website domain")
    platform: Platform = Field(..., description="Ad platform")
    platform_ad_id: str | None = Field(None, description="Ad ID on the platform")
    platform_ad_url: str | None = Field(None, description="URL to view the ad")
    creative_hash: str | None = Field(
        None,
        description="Perceptual hash for matching creatives",
    )
    status: AdStatus = "active"
    is_universal_winner: bool = Field(
        False,
        description="Found on 3+ platforms",
    )


class CrossPlatformAdCreate(CrossPlatformAdBase):
    """Schema for creating cross-platform ad record."""

    ad_id: UUID | None = Field(None, description="Link to our ads table (if Facebook)")


class CrossPlatformAdResponse(CrossPlatformAdBase):
    """Schema for cross-platform ad response."""

    id: UUID
    ad_id: UUID | None = None
    first_seen_at: datetime
    last_seen_at: datetime

    model_config = {"from_attributes": True}


class CrossPlatformAdSummary(BaseModel):
    """Brief summary for embedding in other responses."""

    platform: Platform
    status: AdStatus
    is_universal_winner: bool

    model_config = {"from_attributes": True}


class CrossPlatformSearchRequest(BaseModel):
    """Request to search for ads across platforms."""

    domain: str = Field(..., description="Domain to search for")
    platforms: list[Platform] = Field(
        default=["facebook", "tiktok", "google"],
        description="Platforms to search",
    )


class CrossPlatformSearchResult(BaseModel):
    """Result of cross-platform search for a single platform."""

    platform: Platform
    ads_found: int
    ads: list[CrossPlatformAdResponse] = Field(default_factory=list)
    error: str | None = None


class CrossPlatformSearchResponse(BaseModel):
    """Response from cross-platform search."""

    domain: str
    total_ads_found: int
    platforms_searched: list[Platform]
    results: list[CrossPlatformSearchResult]
    universal_winners: list[CrossPlatformAdResponse] = Field(
        default_factory=list,
        description="Ads found on 3+ platforms",
    )


class UniversalWinnerReport(BaseModel):
    """Report on universal winner ads (found on 3+ platforms)."""

    domain: str
    total_universal_winners: int
    winners: list[CrossPlatformAdResponse]
    platforms_coverage: dict[Platform, int] = Field(
        description="Count of ads per platform",
    )


class TechnicalSophisticationRanking(BaseModel):
    """Competitor ranking by technical sophistication."""

    competitor_id: UUID
    competitor_name: str
    domain: str
    score: int = Field(ge=0, le=100)
    has_meta_pixel: bool
    has_capi: bool
    has_google_ads: bool
    has_tiktok_pixel: bool
    platforms_active: list[Platform]


class TechnicalSophisticationLeaderboard(BaseModel):
    """Leaderboard of competitors by technical sophistication."""

    rankings: list[TechnicalSophisticationRanking]
    your_rank: int | None = None
    your_score: int | None = None
    recommendations: list[str] = Field(default_factory=list)
