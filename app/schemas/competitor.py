"""Competitor schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class CompetitorBase(BaseModel):
    """Base schema for competitor."""

    company_name: str = Field(..., min_length=1, max_length=255)
    ad_library_url: str = Field(..., description="Meta Ad Library URL for this competitor")
    industry: str | None = None
    follower_count: int | None = Field(None, ge=0)
    is_market_leader: bool = False
    market_position: str | None = Field(None, description="e.g., leader, challenger, niche")


class CompetitorCreate(CompetitorBase):
    """Schema for creating a competitor."""

    discovery_method: str = Field(default="manual_add", description="How the competitor was discovered")


class CompetitorUpdate(BaseModel):
    """Schema for updating a competitor."""

    company_name: str | None = Field(None, min_length=1, max_length=255)
    ad_library_url: str | None = None
    industry: str | None = None
    follower_count: int | None = Field(None, ge=0)
    is_market_leader: bool | None = None
    market_position: str | None = None
    active: bool | None = None


class CompetitorResponse(CompetitorBase):
    """Schema for competitor response."""

    id: UUID
    discovery_method: str | None
    discovered_date: datetime
    last_retrieved: datetime | None
    active: bool
    metadata_: dict | None = Field(None, alias="metadata")
    ad_count: int | None = Field(None, description="Number of ads from this competitor")

    model_config = {"from_attributes": True, "populate_by_name": True}


class CompetitorListResponse(BaseModel):
    """Schema for listing competitors."""

    items: list[CompetitorResponse]
    total: int
    page: int
    page_size: int


class CompetitorDiscoverRequest(BaseModel):
    """Request to discover competitors."""

    industry: str | None = Field(None, description="Industry to focus on")
    max_competitors: int = Field(default=10, ge=1, le=50)
    include_market_leaders: bool = True


class CompetitorDiscoverResponse(BaseModel):
    """Response after discovering competitors."""

    discovered: list[CompetitorResponse]
    total_found: int
    already_tracked: int
