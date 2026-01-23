"""Critique endpoint request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.ad_analysis import EnhancedAdAnalysisV2


class CritiqueRequest(BaseModel):
    """Optional context for ad critique analysis."""

    brand_name: str | None = Field(
        None,
        description="Brand/company name for context",
    )
    industry: str | None = Field(
        None,
        description="Industry for context (e.g., 'SaaS', 'E-commerce', 'Health & Fitness')",
    )
    target_audience: str | None = Field(
        None,
        description="Target audience description for context",
    )
    platform_cta: str | None = Field(
        None,
        description="Platform CTA button text (e.g., 'Learn More', 'Shop Now')",
    )


class CritiqueResponse(BaseModel):
    """Response from ad critique analysis."""

    id: UUID | None = Field(
        None,
        description="Critique ID (set when persisted to database)",
    )
    analysis: EnhancedAdAnalysisV2 = Field(
        ...,
        description="Complete enhanced analysis with Creative DNA V2",
    )
    processing_time_seconds: float = Field(
        ...,
        description="Time taken to analyze the ad in seconds",
    )
    model_used: str = Field(
        ...,
        description="Model used for analysis (e.g., 'gemini-2.0-flash', 'gpt-4o')",
    )
    media_type: str = Field(
        ...,
        description="Detected media type: 'video' or 'image'",
    )
    file_size_bytes: int = Field(
        ...,
        description="Size of the uploaded file in bytes",
    )
    file_name: str | None = Field(
        None,
        description="Original file name",
    )
    created_at: datetime | None = Field(
        None,
        description="When the critique was created",
    )


class CritiqueListItem(BaseModel):
    """Summary item for critique list endpoint."""

    id: UUID
    file_name: str
    file_size_bytes: int
    media_type: str
    brand_name: str | None = None
    industry: str | None = None
    overall_grade: str | None = None
    hook_score: int | None = None
    pacing_score: int | None = None
    thumb_stop_score: int | None = None
    model_used: str | None = None
    processing_time_seconds: float | None = None
    created_at: datetime


class CritiqueListResponse(BaseModel):
    """Response for listing critiques."""

    critiques: list[CritiqueListItem]
    total: int
    page: int
    page_size: int


class CritiqueError(BaseModel):
    """Error response from critique endpoint."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Detailed error message")
    details: dict | None = Field(None, description="Additional error details")
