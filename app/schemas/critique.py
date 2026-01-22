"""Critique endpoint request/response schemas."""

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


class CritiqueResponse(BaseModel):
    """Response from ad critique analysis."""

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


class CritiqueError(BaseModel):
    """Error response from critique endpoint."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Detailed error message")
    details: dict | None = Field(None, description="Additional error details")
