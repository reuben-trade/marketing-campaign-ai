"""Pydantic schemas for Recipe extraction and API responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BeatDefinition(BaseModel):
    """Definition of a single beat in a recipe structure."""

    beat_type: str = Field(
        ...,
        description="Type of beat: Hook, Problem, Solution, Product Showcase, Social Proof, etc.",
    )
    target_duration: float = Field(
        ...,
        description="Recommended duration in seconds (guideline, not enforced)",
    )
    characteristics: list[str] = Field(
        default_factory=list,
        description="Visual/audio characteristics: fast_cuts, bold_text, high_energy, etc.",
    )
    purpose: str = Field(
        default="",
        description="The purpose of this beat in the ad narrative",
    )
    cinematics: dict | None = Field(
        default=None,
        description="Cinematic details: camera_angle, lighting_style, motion_type, etc.",
    )
    rhetorical_mode: str | None = Field(
        default=None,
        description="Rhetorical approach: Logos, Pathos, Ethos, Kairos",
    )
    text_overlay_pattern: str | None = Field(
        default=None,
        description="Pattern for text overlays: headline, benefit_list, cta_text, etc.",
    )
    transition_out: str | None = Field(
        default=None,
        description="Transition to next beat: cut, dissolve, wipe, zoom, etc.",
    )


class RecipeCreate(BaseModel):
    """Schema for creating a recipe manually."""

    name: str = Field(..., description="Name for the recipe")
    source_ad_id: uuid.UUID | None = Field(
        default=None,
        description="Optional source ad ID if extracted from an existing ad",
    )
    total_duration_seconds: int | None = Field(
        default=None,
        description="Target total duration in seconds",
    )
    structure: list[BeatDefinition] = Field(
        ...,
        min_length=1,
        description="List of beat definitions that make up the recipe",
    )
    pacing: str | None = Field(
        default=None,
        description="Overall pacing: fast, medium, slow, dynamic",
    )
    style: str | None = Field(
        default=None,
        description="Production style: ugc, polished, cinematic, talking_head, etc.",
    )


class RecipeResponse(BaseModel):
    """Schema for recipe API responses."""

    id: uuid.UUID
    source_ad_id: uuid.UUID | None
    name: str
    total_duration_seconds: int | None
    structure: list[BeatDefinition]
    pacing: str | None
    style: str | None
    composite_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipeListResponse(BaseModel):
    """Schema for listing recipes."""

    recipes: list[RecipeResponse]
    total: int


class RecipeExtractRequest(BaseModel):
    """Schema for requesting recipe extraction from an ad."""

    ad_id: uuid.UUID = Field(..., description="ID of the ad to extract recipe from")
    name: str | None = Field(
        default=None,
        description="Optional custom name for the recipe (auto-generated if not provided)",
    )


class RecipeExtractResponse(BaseModel):
    """Schema for recipe extraction response."""

    recipe: RecipeResponse
    extraction_notes: list[str] = Field(
        default_factory=list,
        description="Notes about the extraction process",
    )


class ReferenceAdFetchRequest(BaseModel):
    """Schema for fetching a reference ad from URL."""

    url: str = Field(
        ...,
        description="URL to fetch the video from",
        pattern=r"^https?://",
        json_schema_extra={"examples": ["https://example.com/video.mp4"]},
    )
    name: str | None = Field(
        default=None,
        description="Optional custom name for the recipe",
    )


class ReferenceAdResponse(BaseModel):
    """Schema for reference ad upload/fetch response."""

    ad_id: uuid.UUID = Field(..., description="ID of the created ad")
    recipe: RecipeResponse | None = Field(
        default=None,
        description="Extracted recipe (None if extraction failed)",
    )
    status: str = Field(..., description="Status: success, partial, error")
    message: str = Field(..., description="Status message")
    processing_notes: list[str] = Field(
        default_factory=list,
        description="Notes about the processing",
    )
