"""Pydantic schemas for user video segments."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserVideoSegmentBase(BaseModel):
    """Base schema for user video segments."""

    source_file_id: uuid.UUID
    source_file_name: str | None = None
    source_file_url: str | None = None
    timestamp_start: float = Field(..., ge=0, description="Start time in seconds")
    timestamp_end: float = Field(..., ge=0, description="End time in seconds")
    visual_description: str | None = None
    action_tags: list[str] | None = None


class UserVideoSegmentCreate(UserVideoSegmentBase):
    """Schema for creating a user video segment."""

    project_id: uuid.UUID
    duration_seconds: float | None = None
    embedding: list[float] | None = None
    thumbnail_url: str | None = None


class UserVideoSegmentUpdate(BaseModel):
    """Schema for updating a user video segment."""

    visual_description: str | None = None
    action_tags: list[str] | None = None
    embedding: list[float] | None = None
    thumbnail_url: str | None = None


class UserVideoSegmentResponse(UserVideoSegmentBase):
    """Schema for user video segment response."""

    id: uuid.UUID
    project_id: uuid.UUID
    duration_seconds: float | None = None
    thumbnail_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserVideoSegmentWithSimilarity(UserVideoSegmentResponse):
    """Schema for user video segment with similarity score (for search results)."""

    similarity_score: float = Field(..., ge=0, le=1)


class SegmentAnalysis(BaseModel):
    """Schema for a single segment extracted from Gemini analysis."""

    timestamp_start: float = Field(..., ge=0, description="Start time in seconds")
    timestamp_end: float = Field(..., ge=0, description="End time in seconds")
    visual_description: str = Field(..., description="Detailed visual description")
    action_tags: list[str] = Field(default_factory=list, description="Tags describing the action")
    scene_type: str | None = Field(
        None,
        description="Type of scene (e.g., 'product_demo', 'testimonial', 'b-roll')",
    )
    emotion: str | None = Field(None, description="Dominant emotion in the segment")
    camera_shot: str | None = Field(
        None, description="Camera shot type (e.g., 'close-up', 'wide', 'medium')"
    )
    motion_type: str | None = Field(
        None, description="Type of motion (e.g., 'static', 'handheld', 'tracking')"
    )
    has_text_overlay: bool = Field(default=False)
    has_face: bool = Field(default=False)
    has_product: bool = Field(default=False)


class VideoAnalysisResult(BaseModel):
    """Schema for the full video analysis result from Gemini."""

    video_level_summary: str = Field(..., description="Overall summary of the video content")
    video_level_tags: list[str] = Field(
        default_factory=list, description="Tags describing the overall video"
    )
    total_duration_seconds: float = Field(..., ge=0)
    segments: list[SegmentAnalysis] = Field(
        default_factory=list, description="Timestamped segments extracted"
    )
    dominant_theme: str | None = Field(
        None, description="Dominant theme of the video (e.g., 'product showcase')"
    )
    production_style: str | None = Field(
        None, description="Production style (e.g., 'UGC', 'professional', 'hybrid')"
    )
    content_type: str | None = Field(
        None,
        description="Content type (e.g., 'demo', 'testimonial', 'lifestyle', 'b-roll')",
    )


class AnalysisProgress(BaseModel):
    """Schema for analysis progress updates."""

    project_id: uuid.UUID
    total_files: int
    completed_files: int
    current_file: str | None = None
    status: str = Field(
        default="pending",
        description="Overall status: pending, processing, completed, failed",
    )
    error_message: str | None = None
    segments_extracted: int = 0


class ProjectSegmentsResponse(BaseModel):
    """Response containing all segments for a project."""

    project_id: uuid.UUID
    total_segments: int
    segments: list[UserVideoSegmentResponse]


class SegmentSearchRequest(BaseModel):
    """Request schema for searching segments."""

    query: str = Field(..., min_length=1, description="Search query for semantic matching")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    min_similarity: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum similarity threshold"
    )


class SegmentSearchResponse(BaseModel):
    """Response containing search results with similarity scores."""

    project_id: uuid.UUID
    query: str
    total_results: int
    results: list[UserVideoSegmentWithSimilarity]
