"""Project schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    """Base schema for project."""

    name: str = Field(..., min_length=1, max_length=200)
    brand_profile_id: UUID | None = None
    user_prompt: str | None = Field(None, description="User prompt for generation")


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    inspiration_ads: list[UUID] | None = Field(None, description="Array of ad IDs for inspiration")
    max_videos: int = Field(default=10, ge=1, le=20)
    max_total_size_mb: int = Field(default=500, ge=100, le=2000)


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=200)
    brand_profile_id: UUID | None = None
    status: str | None = Field(
        None, description="Project status: draft, processing, ready, rendered"
    )
    inspiration_ads: list[UUID] | None = Field(None, description="Array of ad IDs for inspiration")
    user_prompt: str | None = None
    max_videos: int | None = Field(None, ge=1, le=20)
    max_total_size_mb: int | None = Field(None, ge=100, le=2000)


class ProjectStats(BaseModel):
    """Statistics for a project."""

    videos_uploaded: int = 0
    total_size_mb: float = 0.0
    segments_extracted: int = 0


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: UUID
    name: str
    brand_profile_id: UUID | None
    status: str
    inspiration_ads: list[UUID] | None = None
    user_prompt: str | None
    max_videos: int
    max_total_size_mb: int
    created_at: datetime
    updated_at: datetime
    stats: ProjectStats | None = None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Schema for listing projects."""

    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int


# Upload schemas


class ProjectFileResponse(BaseModel):
    """Schema for a single uploaded file response."""

    file_id: UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    file_url: str
    status: str

    model_config = {"from_attributes": True}


class UploadFailure(BaseModel):
    """Schema for a failed upload."""

    filename: str
    error: str


class ProjectUploadResponse(BaseModel):
    """Schema for upload response."""

    project_id: UUID
    uploaded_files: list[ProjectFileResponse]
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    failed_files: list[UploadFailure] = []

    model_config = {"from_attributes": True}


class ProjectFilesListResponse(BaseModel):
    """Schema for listing project files."""

    project_id: UUID
    files: list[ProjectFileResponse]
    total: int
    total_size_bytes: int
    total_size_mb: float


# Ad Generation schemas


class GenerateAdRequest(BaseModel):
    """Request schema for generating an ad from a project."""

    recipe_id: UUID = Field(..., description="ID of the recipe to use as structural template")
    user_prompt: str | None = Field(
        None,
        description="Optional user prompt for creative direction (e.g., 'Focus on the discount')",
    )
    composition_type: str = Field(
        default="vertical_ad_v1",
        description="Composition type: vertical_ad_v1, horizontal_ad_v1, square_ad_v1",
    )
    min_similarity_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for clip selection",
    )
    gap_handling: str = Field(
        default="broll",
        description="How to handle gaps: 'broll' (generate B-Roll), 'text_slide', or 'skip'",
    )
    audio_url: str | None = Field(
        None,
        description="Optional background audio track URL",
    )


class GenerationStats(BaseModel):
    """Statistics from the ad generation process."""

    total_slots: int = Field(..., description="Total number of slots in the visual script")
    clips_selected: int = Field(..., description="Number of slots filled with user clips")
    gaps_detected: int = Field(..., description="Number of slots with no matching clips")
    coverage_percentage: float = Field(..., description="Percentage of slots with clips")
    average_similarity: float = Field(..., description="Average similarity score of selected clips")
    total_duration_seconds: float = Field(..., description="Total video duration in seconds")


class GenerateAdResponse(BaseModel):
    """Response schema for ad generation endpoint."""

    project_id: UUID
    visual_script_id: UUID
    payload_preview: dict = Field(
        ..., description="Preview of the Remotion payload (composition, duration, timeline summary)"
    )
    stats: GenerationStats
    gaps: list[dict] | None = Field(
        None,
        description="Detected gaps where no suitable clip was found",
    )
    warnings: list[str] | None = Field(
        None,
        description="Warnings about the assembly (duration mismatches, etc.)",
    )
    success: bool = True
