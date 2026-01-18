"""Business Strategy schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TargetAudience(BaseModel):
    """Target audience information."""

    demographics: str = Field(..., description="Demographic characteristics")
    psychographics: str = Field(..., description="Psychographic profile")
    pain_points: list[str] = Field(default_factory=list, description="Key pain points")


class BrandVoice(BaseModel):
    """Brand voice characteristics."""

    tone: str = Field(..., description="Brand tone (e.g., professional, casual, playful)")
    personality_traits: list[str] = Field(default_factory=list, description="Brand personality traits")
    messaging_guidelines: str = Field(..., description="Guidelines for messaging")


class BusinessStrategyBase(BaseModel):
    """Base schema for business strategy."""

    business_name: str = Field(..., min_length=1, max_length=255)
    business_description: str | None = None
    industry: str | None = None
    target_audience: TargetAudience | None = None
    brand_voice: BrandVoice | None = None
    market_position: str | None = Field(None, description="e.g., challenger, leader, niche")
    price_point: str | None = Field(None, description="e.g., premium, mid-market, budget")
    business_life_stage: str | None = Field(None, description="e.g., startup, growth, mature")
    unique_selling_points: list[str] | None = None
    competitive_advantages: list[str] | None = None
    marketing_objectives: list[str] | None = None


class BusinessStrategyCreate(BusinessStrategyBase):
    """Schema for creating a business strategy."""

    pass


class BusinessStrategyUpdate(BaseModel):
    """Schema for updating a business strategy."""

    business_name: str | None = Field(None, min_length=1, max_length=255)
    business_description: str | None = None
    industry: str | None = None
    target_audience: TargetAudience | None = None
    brand_voice: BrandVoice | None = None
    market_position: str | None = None
    price_point: str | None = None
    business_life_stage: str | None = None
    unique_selling_points: list[str] | None = None
    competitive_advantages: list[str] | None = None
    marketing_objectives: list[str] | None = None


class BusinessStrategyResponse(BusinessStrategyBase):
    """Schema for business strategy response."""

    id: UUID
    raw_pdf_url: str | None = None
    extracted_date: datetime
    last_updated: datetime

    model_config = {"from_attributes": True}


class BusinessStrategyExtractRequest(BaseModel):
    """Request to extract strategy from PDF."""

    pdf_url: str = Field(..., description="URL of the uploaded PDF in Supabase Storage")


class BusinessStrategyExtractResponse(BaseModel):
    """Response after extracting strategy from PDF."""

    strategy: BusinessStrategyResponse
    extraction_confidence: float = Field(..., ge=0, le=1, description="Confidence in extraction quality")
    missing_fields: list[str] = Field(default_factory=list, description="Fields that couldn't be extracted")
