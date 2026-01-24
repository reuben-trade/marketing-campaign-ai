"""Search and relevance schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.ad import AdResponse


class SemanticSearchRequest(BaseModel):
    """Request for semantic search."""

    query: str = Field(..., min_length=1, description="Search query text")
    filters: dict[str, Any] | None = Field(None, description="Additional filters (creative_type, analyzed, etc.)")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")


class AdWithSimilarity(AdResponse):
    """Ad response with similarity score."""

    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")


class SemanticSearchResponse(BaseModel):
    """Response for semantic search."""

    items: list[AdWithSimilarity]
    total: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original search query")


class RelevanceFilter(BaseModel):
    """Filter for relevance-based ad selection."""

    description: str = Field(..., min_length=1, description="Description of what to advertise")
    themes: list[str] = Field(default_factory=list, description="Specific themes or ideas to focus on")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")


class SimilarAdsRequest(BaseModel):
    """Request for finding similar ads."""

    ad_id: UUID = Field(..., description="ID of ad to find similar ads for")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")


class EmbedAdsRequest(BaseModel):
    """Request for generating embeddings for ads."""

    limit: int = Field(100, ge=1, le=1000, description="Maximum number of ads to process")


class EmbedAdsResponse(BaseModel):
    """Response after embedding ads."""

    processed: int = Field(..., description="Number of ads processed")
    failed: int = Field(..., description="Number of ads that failed")


class ScoreCalculationResponse(BaseModel):
    """Response after calculating scores."""

    processed: int = Field(..., description="Number of ads processed")
    failed: int = Field(..., description="Number of ads that failed")


class PercentileRecalculationResponse(BaseModel):
    """Response after recalculating percentiles."""

    processed: int = Field(..., description="Number of ads processed")
    skipped: int = Field(..., description="Number of ads skipped")
