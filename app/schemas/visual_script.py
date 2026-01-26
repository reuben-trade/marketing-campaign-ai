"""Pydantic schemas for Visual Script generation and API responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VisualScriptSlot(BaseModel):
    """A single slot in a visual script representing one beat/segment of the ad."""

    id: str = Field(
        ...,
        description="Unique identifier for this slot (e.g., 'slot_01_hook')",
    )
    beat_type: str = Field(
        ...,
        description="Type of beat: Hook, Problem, Solution, Product Showcase, Social Proof, etc.",
    )
    target_duration: float = Field(
        ...,
        description="Target duration in seconds for this slot",
    )
    search_query: str = Field(
        ...,
        description="Semantic search query to find matching user clips",
    )
    overlay_text: str | None = Field(
        default=None,
        description="Text to display as overlay on this slot",
    )
    text_position: str | None = Field(
        default=None,
        description="Position of text overlay: top, center, bottom, lower-third",
    )
    transition_in: str | None = Field(
        default=None,
        description="Transition effect from previous slot: cut, dissolve, wipe, zoom, etc.",
    )
    transition_out: str | None = Field(
        default=None,
        description="Transition effect to next slot: cut, dissolve, wipe, zoom, etc.",
    )
    notes: str | None = Field(
        default=None,
        description="Additional notes about clip requirements or creative direction",
    )
    characteristics: list[str] = Field(
        default_factory=list,
        description="Visual/audio characteristics needed: fast_cuts, bold_text, etc.",
    )
    cinematics: dict | None = Field(
        default=None,
        description="Cinematic requirements: camera_angle, lighting, motion_type, etc.",
    )


class VisualScriptGenerateRequest(BaseModel):
    """Request schema for generating a visual script."""

    project_id: uuid.UUID = Field(
        ...,
        description="ID of the project to generate script for",
    )
    recipe_id: uuid.UUID = Field(
        ...,
        description="ID of the recipe to use as structural template",
    )
    user_prompt: str | None = Field(
        default=None,
        description="Optional user prompt for creative direction (e.g., 'Focus on the discount')",
    )


class VisualScriptCreate(BaseModel):
    """Schema for creating a visual script."""

    project_id: uuid.UUID
    recipe_id: uuid.UUID | None = None
    total_duration_seconds: int | None = None
    slots: list[VisualScriptSlot]
    audio_suggestion: str | None = None
    pacing_notes: str | None = None


class VisualScriptResponse(BaseModel):
    """Schema for visual script API responses."""

    id: uuid.UUID
    project_id: uuid.UUID
    recipe_id: uuid.UUID | None
    total_duration_seconds: int | None
    slots: list[VisualScriptSlot]
    audio_suggestion: str | None
    pacing_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VisualScriptListResponse(BaseModel):
    """Schema for listing visual scripts."""

    scripts: list[VisualScriptResponse]
    total: int


class ContentPlanningInput(BaseModel):
    """Input data assembled for the content planning agent."""

    recipe_name: str
    recipe_structure: list[dict]
    recipe_pacing: str | None
    recipe_style: str | None
    total_target_duration: int | None
    user_content_summaries: list[str]
    user_prompt: str | None
    brand_profile: dict | None


class ContentPlanningOutput(BaseModel):
    """Output from the content planning agent."""

    slots: list[VisualScriptSlot]
    total_duration_seconds: int
    audio_suggestion: str | None = None
    pacing_notes: str | None = None
    planning_notes: list[str] = Field(
        default_factory=list,
        description="Notes from the planning process",
    )
