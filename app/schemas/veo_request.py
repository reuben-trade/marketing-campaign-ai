"""Pydantic schemas for Veo 2 B-Roll generation requests and responses."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class VeoAspectRatio(str, Enum):
    """Supported aspect ratios for Veo 2 generation."""

    VERTICAL = "9:16"  # Stories/Reels/TikTok
    HORIZONTAL = "16:9"  # YouTube/Facebook Feed
    SQUARE = "1:1"  # Instagram Feed


class VeoStyle(str, Enum):
    """Supported generation styles for Veo 2."""

    REALISTIC = "realistic"
    CINEMATIC = "cinematic"
    ANIMATED = "animated"
    ARTISTIC = "artistic"


class VeoGenerationStatus(str, Enum):
    """Status of a Veo generation job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VeoGenerateRequest(BaseModel):
    """Request to generate B-Roll clip using Veo 2."""

    prompt: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Descriptive prompt for video generation",
    )
    duration_seconds: float = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="Duration of the generated clip in seconds (1-10)",
    )
    aspect_ratio: VeoAspectRatio = Field(
        default=VeoAspectRatio.VERTICAL,
        description="Aspect ratio for the generated video",
    )
    style: VeoStyle = Field(
        default=VeoStyle.REALISTIC,
        description="Visual style for generation",
    )
    num_variants: int = Field(
        default=2,
        ge=1,
        le=4,
        description="Number of variant clips to generate (1-4)",
    )
    project_id: uuid.UUID | None = Field(
        default=None,
        description="Optional project ID to associate with generated clips",
    )
    slot_id: str | None = Field(
        default=None,
        description="Optional visual script slot ID this B-Roll is for",
    )
    negative_prompt: str | None = Field(
        default=None,
        max_length=500,
        description="Negative prompt describing what to avoid",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible generation",
    )


class VeoRegenerateRequest(BaseModel):
    """Request to regenerate B-Roll with a modified prompt."""

    original_generation_id: uuid.UUID = Field(
        ...,
        description="ID of the original generation to regenerate from",
    )
    prompt: str | None = Field(
        default=None,
        min_length=10,
        max_length=1000,
        description="Modified prompt (uses original if not provided)",
    )
    duration_seconds: float | None = Field(
        default=None,
        ge=1.0,
        le=10.0,
        description="New duration (uses original if not provided)",
    )
    style: VeoStyle | None = Field(
        default=None,
        description="New style (uses original if not provided)",
    )
    num_variants: int | None = Field(
        default=None,
        ge=1,
        le=4,
        description="New number of variants (uses original if not provided)",
    )
    negative_prompt: str | None = Field(
        default=None,
        max_length=500,
        description="New negative prompt",
    )


class VeoGeneratedClip(BaseModel):
    """A single generated video clip variant."""

    id: uuid.UUID = Field(..., description="Unique identifier for this clip")
    url: str | None = Field(default=None, description="URL to the generated video file")
    thumbnail_url: str | None = Field(default=None, description="URL to video thumbnail")
    duration_seconds: float = Field(..., description="Actual duration of generated clip")
    width: int = Field(..., description="Video width in pixels")
    height: int = Field(..., description="Video height in pixels")
    file_size_bytes: int | None = Field(default=None, description="Size of video file in bytes")
    variant_index: int = Field(..., description="Index of this variant (0-based)")


class VeoGenerationResponse(BaseModel):
    """Response from a Veo 2 generation request."""

    id: uuid.UUID = Field(..., description="Generation job ID")
    status: VeoGenerationStatus = Field(..., description="Current status of generation")
    prompt: str = Field(..., description="The prompt used for generation")
    duration_seconds: float = Field(..., description="Requested duration")
    aspect_ratio: VeoAspectRatio = Field(..., description="Aspect ratio used")
    style: VeoStyle = Field(..., description="Style used for generation")
    num_variants: int = Field(..., description="Number of variants requested")
    clips: list[VeoGeneratedClip] = Field(
        default_factory=list,
        description="Generated clip variants (populated when completed)",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if generation failed",
    )
    project_id: uuid.UUID | None = Field(default=None, description="Associated project ID")
    slot_id: str | None = Field(default=None, description="Associated visual script slot ID")
    created_at: datetime = Field(..., description="When generation was requested")
    completed_at: datetime | None = Field(default=None, description="When generation completed")
    generation_time_seconds: float | None = Field(
        default=None,
        description="Time taken to generate clips",
    )


class VeoGenerationStatusResponse(BaseModel):
    """Response for checking generation status."""

    id: uuid.UUID = Field(..., description="Generation job ID")
    status: VeoGenerationStatus = Field(..., description="Current status")
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Progress percentage (0-100)",
    )
    clips: list[VeoGeneratedClip] = Field(
        default_factory=list,
        description="Generated clips if completed",
    )
    error_message: str | None = Field(default=None, description="Error if failed")
    estimated_time_remaining_seconds: float | None = Field(
        default=None,
        description="Estimated time remaining",
    )


class VeoGenerationListResponse(BaseModel):
    """Response for listing generation jobs."""

    generations: list[VeoGenerationResponse] = Field(
        ...,
        description="List of generation jobs",
    )
    total: int = Field(..., description="Total number of generations")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


class VeoSelectClipRequest(BaseModel):
    """Request to select a generated clip for use in the timeline."""

    generation_id: uuid.UUID = Field(..., description="Generation job ID")
    clip_id: uuid.UUID = Field(..., description="ID of the clip to select")


class VeoSelectClipResponse(BaseModel):
    """Response after selecting a clip."""

    clip: VeoGeneratedClip = Field(..., description="The selected clip")
    storage_url: str = Field(
        ...,
        description="Permanent storage URL for the clip (moved to project storage)",
    )


class PromptEnhancementRequest(BaseModel):
    """Request to enhance a B-Roll prompt using AI."""

    original_prompt: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Original user prompt to enhance",
    )
    context: str | None = Field(
        default=None,
        max_length=500,
        description="Context about the ad/scene for better enhancement",
    )
    style_hints: list[str] | None = Field(
        default=None,
        description="Hints about desired style (e.g., 'professional', 'energetic')",
    )


class PromptEnhancementResponse(BaseModel):
    """Response with enhanced prompt suggestions."""

    original_prompt: str = Field(..., description="The original prompt")
    enhanced_prompts: list[str] = Field(
        ...,
        description="List of enhanced prompt suggestions",
    )
    style_recommendations: list[VeoStyle] = Field(
        default_factory=list,
        description="Recommended styles for this content",
    )
