"""Brand profile schemas for onboarding."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BrandProfileBase(BaseModel):
    """Base schema for brand profile."""

    industry: str = Field(..., min_length=1, max_length=100, description="Industry category")
    niche: str | None = Field(None, max_length=200, description="Specific niche within industry")
    core_offer: str | None = Field(
        None, max_length=1000, description="Main product/service offering"
    )


class BrandProfileCreate(BrandProfileBase):
    """Schema for creating a brand profile via onboarding."""

    competitors: list[UUID] | None = Field(
        None, description="List of competitor ad IDs for reference"
    )
    keywords: list[str] | None = Field(None, description="Keywords that define the brand")
    tone: str | None = Field(
        None,
        max_length=50,
        description="Brand voice tone (e.g., professional_friendly, casual, authoritative)",
    )
    forbidden_terms: list[str] | None = Field(
        None, description="Terms to avoid in generated content"
    )
    logo_url: str | None = Field(None, description="URL to brand logo")
    primary_color: str | None = Field(
        None, pattern="^#[0-9A-Fa-f]{6}$", description="Primary brand color in hex format"
    )
    font_family: str | None = Field(None, max_length=100, description="Preferred font family")


class BrandProfileUpdate(BaseModel):
    """Schema for updating a brand profile."""

    industry: str | None = Field(None, min_length=1, max_length=100)
    niche: str | None = Field(None, max_length=200)
    core_offer: str | None = Field(None, max_length=1000)
    competitors: list[UUID] | None = None
    keywords: list[str] | None = None
    tone: str | None = Field(None, max_length=50)
    forbidden_terms: list[str] | None = None
    logo_url: str | None = None
    primary_color: str | None = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    font_family: str | None = Field(None, max_length=100)


class BrandProfileResponse(BaseModel):
    """Schema for brand profile response."""

    id: UUID
    industry: str
    niche: str | None
    core_offer: str | None
    competitors: list[UUID] | None = None
    keywords: list[str] | None = None
    tone: str | None
    forbidden_terms: list[str] | None = None
    logo_url: str | None
    primary_color: str | None
    font_family: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BrandProfileListResponse(BaseModel):
    """Schema for listing brand profiles."""

    items: list[BrandProfileResponse]
    total: int
    page: int
    page_size: int


# Onboarding-specific schemas for the 3-step flow


class OnboardingStep1Request(BaseModel):
    """Step 1: Industry/Niche selection."""

    industry: str = Field(..., min_length=1, max_length=100, description="Industry category")
    niche: str | None = Field(None, max_length=200, description="Specific niche within industry")


class OnboardingStep2Request(BaseModel):
    """Step 2: Core Offer description."""

    core_offer: str = Field(
        ..., min_length=10, max_length=1000, description="Main product/service offering"
    )
    keywords: list[str] | None = Field(
        None, max_length=10, description="Keywords that define the brand"
    )
    tone: str | None = Field(
        None,
        max_length=50,
        description="Brand voice tone (e.g., professional_friendly, casual, authoritative)",
    )


class OnboardingStep3Request(BaseModel):
    """Step 3: Competitors selection."""

    competitors: list[UUID] | None = Field(
        None, max_length=5, description="List of competitor ad IDs for reference"
    )
    forbidden_terms: list[str] | None = Field(
        None, max_length=20, description="Terms to avoid in generated content"
    )


class OnboardingCompleteRequest(BaseModel):
    """Complete onboarding flow - all steps in one request."""

    # Step 1
    industry: str = Field(..., min_length=1, max_length=100, description="Industry category")
    niche: str | None = Field(None, max_length=200, description="Specific niche within industry")

    # Step 2
    core_offer: str = Field(
        ..., min_length=10, max_length=1000, description="Main product/service offering"
    )
    keywords: list[str] | None = Field(
        None, max_length=10, description="Keywords that define the brand"
    )
    tone: str | None = Field(
        None,
        max_length=50,
        description="Brand voice tone",
    )

    # Step 3
    competitors: list[UUID] | None = Field(
        None, max_length=5, description="List of competitor ad IDs"
    )
    forbidden_terms: list[str] | None = Field(None, max_length=20, description="Terms to avoid")

    # Optional visual identity
    logo_url: str | None = Field(None, description="URL to brand logo")
    primary_color: str | None = Field(
        None, pattern="^#[0-9A-Fa-f]{6}$", description="Primary brand color in hex format"
    )
    font_family: str | None = Field(None, max_length=100, description="Preferred font family")


class OnboardingStatusResponse(BaseModel):
    """Response for checking onboarding status."""

    has_brand_profile: bool
    brand_profile: BrandProfileResponse | None = None
    completed_steps: int = Field(
        ..., ge=0, le=3, description="Number of completed onboarding steps (0-3)"
    )


# Industry options for the onboarding UI
INDUSTRY_OPTIONS = [
    {"value": "ecommerce", "label": "E-commerce / Retail"},
    {"value": "saas", "label": "SaaS / Software"},
    {"value": "home_services", "label": "Home Services"},
    {"value": "health_fitness", "label": "Health & Fitness"},
    {"value": "beauty_cosmetics", "label": "Beauty & Cosmetics"},
    {"value": "food_beverage", "label": "Food & Beverage"},
    {"value": "education", "label": "Education / Online Courses"},
    {"value": "finance", "label": "Finance / Fintech"},
    {"value": "real_estate", "label": "Real Estate"},
    {"value": "automotive", "label": "Automotive"},
    {"value": "travel", "label": "Travel & Hospitality"},
    {"value": "entertainment", "label": "Entertainment / Media"},
    {"value": "legal", "label": "Legal Services"},
    {"value": "healthcare", "label": "Healthcare / Medical"},
    {"value": "technology", "label": "Technology / Electronics"},
    {"value": "other", "label": "Other"},
]

TONE_OPTIONS = [
    {"value": "professional_friendly", "label": "Professional & Friendly"},
    {"value": "casual", "label": "Casual & Conversational"},
    {"value": "authoritative", "label": "Authoritative & Expert"},
    {"value": "playful", "label": "Playful & Fun"},
    {"value": "luxurious", "label": "Luxurious & Premium"},
    {"value": "urgent", "label": "Urgent & Action-Oriented"},
    {"value": "empathetic", "label": "Empathetic & Understanding"},
    {"value": "inspirational", "label": "Inspirational & Motivational"},
]
