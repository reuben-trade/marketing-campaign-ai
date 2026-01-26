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
    status: str | None = Field(None, description="Project status: draft, processing, ready, rendered")
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
