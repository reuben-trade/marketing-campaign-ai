"""Competitor schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


class CompetitorBase(BaseModel):
    """Base schema for competitor."""

    company_name: str = Field(..., min_length=1, max_length=255)
    page_id: str = Field(..., description="Meta/Facebook Page ID for this competitor")
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
    page_id: str | None = None
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

    @field_validator("metadata_", mode="before")
    @classmethod
    def convert_metadata_to_dict(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        # Handle SQLAlchemy/other ORM objects that aren't plain dicts
        return dict(v) if hasattr(v, "__iter__") else None

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


class PendingCompetitor(BaseModel):
    """Competitor that needs manual Page ID entry."""

    company_name: str
    facebook_page_url: str | None = None
    relevance_reason: str | None = None
    description: str | None = None


class CompetitorDiscoverResponse(BaseModel):
    """Response after discovering competitors."""

    discovered: list[CompetitorResponse]
    total_found: int
    already_tracked: int
    pending_manual_review: list[PendingCompetitor] = Field(
        default_factory=list,
        description="Competitors found but missing Page ID - need manual entry",
    )
