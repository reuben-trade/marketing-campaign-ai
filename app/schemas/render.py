"""Pydantic schemas for video rendering API."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.remotion_payload import RemotionPayload


class RenderStatus(str, Enum):
    """Status of a render job."""

    PENDING = "pending"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class RenderMode(str, Enum):
    """Rendering mode."""

    LOCAL = "local"  # Local Remotion CLI rendering
    LAMBDA = "lambda"  # AWS Lambda rendering


class RenderRequest(BaseModel):
    """Request to start a new render job."""

    project_id: uuid.UUID = Field(..., description="Project ID")
    payload: RemotionPayload = Field(..., description="Remotion payload to render")
    mode: RenderMode = Field(
        default=RenderMode.LOCAL,
        description="Rendering mode (local or lambda)",
    )
    priority: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Render priority (0=normal, 10=highest)",
    )


class RenderResponse(BaseModel):
    """Response after creating a render job."""

    id: uuid.UUID = Field(..., description="Render job ID")
    project_id: uuid.UUID = Field(..., description="Project ID")
    composition_id: str = Field(..., description="Remotion composition ID")
    status: RenderStatus = Field(..., description="Current render status")
    created_at: datetime = Field(..., description="When the render was created")

    # Output (populated when completed)
    video_url: str | None = Field(default=None, description="URL to rendered video")
    thumbnail_url: str | None = Field(default=None, description="URL to thumbnail")

    # Metadata (populated when completed)
    duration_seconds: float | None = Field(default=None, description="Video duration")
    file_size_bytes: int | None = Field(default=None, description="File size in bytes")
    render_time_seconds: float | None = Field(
        default=None,
        description="Time taken to render",
    )

    # Error info (populated if failed)
    error_message: str | None = Field(default=None, description="Error message if failed")

    model_config = {"from_attributes": True}


class RenderStatusResponse(BaseModel):
    """Detailed render status response."""

    id: uuid.UUID = Field(..., description="Render job ID")
    project_id: uuid.UUID = Field(..., description="Project ID")
    composition_id: str = Field(..., description="Remotion composition ID")
    status: RenderStatus = Field(..., description="Current render status")
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Render progress percentage",
    )

    # Output (populated when completed)
    video_url: str | None = Field(default=None, description="URL to rendered video")
    thumbnail_url: str | None = Field(default=None, description="URL to thumbnail")

    # Metadata
    duration_seconds: float | None = Field(default=None, description="Video duration")
    file_size_bytes: int | None = Field(default=None, description="File size in bytes")
    render_time_seconds: float | None = Field(
        default=None,
        description="Time taken to render",
    )

    # Timestamps
    created_at: datetime = Field(..., description="When the render was created")
    started_at: datetime | None = Field(default=None, description="When rendering started")
    completed_at: datetime | None = Field(default=None, description="When rendering completed")

    # Error info
    error_message: str | None = Field(default=None, description="Error message if failed")

    model_config = {"from_attributes": True}


class RenderPayloadUpdate(BaseModel):
    """Request to update a render's payload before rendering starts."""

    payload: RemotionPayload = Field(..., description="Updated Remotion payload")


class RenderListResponse(BaseModel):
    """List of renders for a project."""

    renders: list[RenderResponse] = Field(default_factory=list, description="List of renders")
    total: int = Field(..., description="Total number of renders")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Items per page")


class RenderCallbackPayload(BaseModel):
    """Callback payload from render worker/Lambda."""

    render_id: uuid.UUID = Field(..., description="Render job ID")
    status: RenderStatus = Field(..., description="New status")
    video_url: str | None = Field(default=None, description="URL to rendered video")
    thumbnail_url: str | None = Field(default=None, description="URL to thumbnail")
    duration_seconds: float | None = Field(default=None, description="Video duration")
    file_size_bytes: int | None = Field(default=None, description="File size in bytes")
    render_time_seconds: float | None = Field(default=None, description="Time taken to render")
    error_message: str | None = Field(default=None, description="Error message if failed")


class RenderQueueStats(BaseModel):
    """Statistics about the render queue."""

    pending_count: int = Field(default=0, description="Jobs waiting to render")
    rendering_count: int = Field(default=0, description="Jobs currently rendering")
    completed_today: int = Field(default=0, description="Jobs completed today")
    failed_today: int = Field(default=0, description="Jobs failed today")
    avg_render_time_seconds: float | None = Field(
        default=None,
        description="Average render time today",
    )
