"""Ad schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FormFieldsSchema(BaseModel):
    """Schema for lead gen form fields extracted from ads."""

    intro_text: str | None = Field(None, description="Introduction text for the form")
    questions: list[dict] = Field(
        default_factory=list,
        description="Questions with options, e.g., [{'question': 'Are you a Home Owner?', 'options': ['Yes', 'No']}]",
    )
    fields: list[str] = Field(
        default_factory=list,
        description="Form field names, e.g., ['Full name', 'Email', 'Phone number']",
    )
    terms_links: list[dict] = Field(
        default_factory=list,
        description="Terms/privacy links, e.g., [{'text': 'Terms and Conditions', 'url': '...'}]",
    )
    thank_you_text: str | None = Field(None, description="Thank you message after form submission")


class MarketingEffectiveness(BaseModel):
    """Marketing effectiveness scores."""

    hook_strength: int = Field(..., ge=1, le=10, description="Attention grabbing score")
    message_clarity: int = Field(..., ge=1, le=10, description="Value proposition clarity")
    visual_impact: int = Field(..., ge=1, le=10, description="Production quality and design")
    cta_effectiveness: int = Field(..., ge=1, le=10, description="Call-to-action effectiveness")
    overall_score: int = Field(..., ge=1, le=10, description="Overall marketing score")


class VideoAnalysis(BaseModel):
    """Video-specific analysis (for video ads only)."""

    pacing: str = Field(..., description="Scene changes, rhythm, energy")
    audio_strategy: str = Field(..., description="Music, voiceover, SFX")
    story_arc: str = Field(..., description="Narrative structure and flow")
    caption_usage: str = Field(..., description="Text overlay effectiveness")
    optimal_length: str = Field(..., description="Duration appropriateness")


class AdAnalysis(BaseModel):
    """Complete ad analysis result."""

    summary: str = Field(..., description="2-3 sentence overview")
    insights: list[str] = Field(default_factory=list, description="Key insights")
    uvps: list[str] = Field(default_factory=list, description="Unique value propositions")
    ctas: list[str] = Field(default_factory=list, description="Calls to action used")
    visual_themes: list[str] = Field(default_factory=list, description="Visual style themes")
    target_audience: str = Field(..., description="Target audience description")
    emotional_appeal: str = Field(..., description="Primary emotion triggered")
    marketing_effectiveness: MarketingEffectiveness
    strategic_insights: str = Field(..., description="Marketing strategy analysis")
    reasoning: str = Field(..., description="Detailed explanation of scores")
    video_analysis: VideoAnalysis | None = Field(None, description="Video-specific analysis")


class AdBase(BaseModel):
    """Base schema for ad."""

    ad_library_id: str = Field(..., description="Meta Ad Library ID")
    ad_snapshot_url: str | None = None
    creative_type: str = Field(..., pattern="^(image|video)$")
    creative_storage_path: str = Field(..., description="Supabase storage path")
    creative_url: str | None = Field(None, description="Original Meta CDN URL")
    ad_copy: str | None = None
    ad_headline: str | None = None
    ad_description: str | None = None
    cta_text: str | None = None
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    impressions: int | None = Field(None, ge=0)
    publication_date: datetime | None = None

    # Detailed ad info from modal view
    started_running_date: date | None = Field(None, description="Date the ad started running")
    total_active_time: str | None = Field(None, description="How long ad has been active (e.g., '4 hrs', '3 days')")
    platforms: list[str] | None = Field(None, description="Platforms where ad runs (facebook, instagram, messenger)")
    link_headline: str | None = Field(None, description="Link preview headline")
    link_description: str | None = Field(None, description="Link preview description")
    additional_links: list[str] | None = Field(None, description="Additional URLs from ad assets")
    form_fields: FormFieldsSchema | None = Field(None, description="Lead gen form fields")


class AdCreate(AdBase):
    """Schema for creating an ad."""

    competitor_id: UUID


class AdResponse(AdBase):
    """Schema for ad response."""

    id: UUID
    competitor_id: UUID
    analysis: AdAnalysis | None = None
    retrieved_date: datetime
    analyzed_date: datetime | None = None
    analyzed: bool
    download_status: str
    analysis_status: str
    total_engagement: int = Field(..., description="Sum of likes, comments, shares")
    overall_score: float | None = Field(None, description="Overall marketing score")

    model_config = {"from_attributes": True}


class AdListResponse(BaseModel):
    """Schema for listing ads."""

    items: list[AdResponse]
    total: int
    page: int
    page_size: int


class AdStats(BaseModel):
    """Ad statistics."""

    total_ads: int
    analyzed_ads: int
    pending_analysis: int
    failed_analysis: int
    by_type: dict[str, int] = Field(description="Count by creative type")
    avg_engagement: float
    avg_score: float | None
    top_performer_id: UUID | None


class AdRetrieveRequest(BaseModel):
    """Request to retrieve ads for a competitor."""

    competitor_id: UUID
    max_ads: int | None = Field(None, ge=1, le=100)
    since_days: int | None = Field(None, ge=1, le=365)
    scrape_details: bool = Field(True, description="Scrape detailed modal info for each ad (slower but more accurate)")


class AdRetrieveResponse(BaseModel):
    """Response after retrieving ads."""

    retrieved: int
    skipped: int
    failed: int
    competitor_id: UUID
