"""Ad creative analysis schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

CreativeArchetype = Literal[
    "UGC",
    "Problem/Solution Demo",
    "Lo-fi Meme",
    "High-Production Studio",
]

PrimaryEmotion = Literal[
    "urgency",
    "aspiration",
    "fear",
    "belonging",
    "curiosity",
]

OfferType = Literal[
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


class AdCreativeAnalysisBase(BaseModel):
    """Base schema for ad creative analysis."""

    creative_archetype: CreativeArchetype | None = Field(
        None,
        description="Creative style classification",
    )
    archetype_confidence: Decimal | None = Field(
        None,
        ge=0,
        le=1,
        description="Confidence score for archetype",
    )
    hook_offer_type: OfferType | None = Field(
        None,
        description="Type of hook/offer detected",
    )
    offer_details: str | None = Field(None, description="Specific offer text")
    offer_confidence: Decimal | None = Field(None, ge=0, le=1)
    primary_emotion: PrimaryEmotion | None = Field(
        None,
        description="Primary emotion targeted",
    )
    production_quality_score: int | None = Field(None, ge=1, le=10)
    text_to_image_ratio: Decimal | None = Field(
        None,
        ge=0,
        le=100,
        description="Percentage of image covered by text",
    )
    color_palette: list[str] | None = Field(
        None,
        description="Dominant colors as hex codes",
    )
    has_human_face: bool | None = None
    has_product_shot: bool | None = None


class AdCreativeAnalysisCreate(AdCreativeAnalysisBase):
    """Schema for creating ad creative analysis."""

    ad_id: UUID
    model_used: str | None = None


class AdCreativeAnalysisResponse(AdCreativeAnalysisBase):
    """Schema for ad creative analysis response."""

    id: UUID
    ad_id: UUID
    analysis_date: datetime
    model_used: str | None = None

    model_config = {"from_attributes": True}


class AdCreativeAnalysisSummary(BaseModel):
    """Brief summary for embedding in ad responses."""

    creative_archetype: CreativeArchetype | None = None
    hook_offer_type: OfferType | None = None
    primary_emotion: PrimaryEmotion | None = None
    production_quality_score: int | None = None

    model_config = {"from_attributes": True}


class CreativeAnalysisRequest(BaseModel):
    """Request to analyze an ad creative."""

    ad_id: UUID
    force_reanalyze: bool = Field(False, description="Reanalyze even if already done")


class ArchetypeDistribution(BaseModel):
    """Distribution of creative archetypes for a competitor."""

    ugc: int = Field(0, alias="UGC")
    problem_solution: int = Field(0, alias="Problem/Solution Demo")
    lo_fi_meme: int = Field(0, alias="Lo-fi Meme")
    high_production: int = Field(0, alias="High-Production Studio")
    unknown: int = 0


class OfferDistribution(BaseModel):
    """Distribution of offer types for a competitor."""

    free_quote: int = 0
    percentage_discount: int = 0
    dollar_off: int = 0
    bogo: int = 0
    free_shipping: int = 0
    free_trial: int = 0
    limited_time: int = 0
    no_offer: int = 0
    other: int = 0


class CreativeDiversityReport(BaseModel):
    """Report on creative diversity for a competitor."""

    competitor_id: UUID
    total_ads_analyzed: int
    archetype_distribution: ArchetypeDistribution
    offer_distribution: OfferDistribution
    avg_production_quality: float | None = None
    dominant_emotion: PrimaryEmotion | None = None
    recommendations: list[str] = Field(default_factory=list)
