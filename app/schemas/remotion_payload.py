"""Pydantic schemas for Remotion video payload generation."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CompositionType(str, Enum):
    """Available Remotion composition types (aspect ratios)."""

    VERTICAL = "vertical_ad_v1"  # 9:16 - Stories/Reels/TikTok
    HORIZONTAL = "horizontal_ad_v1"  # 16:9 - YouTube/Facebook Feed
    SQUARE = "square_ad_v1"  # 1:1 - Instagram Feed


class SegmentType(str, Enum):
    """Types of segments in the timeline."""

    VIDEO_CLIP = "video_clip"
    GENERATED_BROLL = "generated_broll"
    TEXT_SLIDE = "text_slide"


class TransitionType(str, Enum):
    """Available transition types."""

    CUT = "cut"
    DISSOLVE = "dissolve"
    FADE = "fade"
    WIPE_RIGHT = "wipe_right"
    WIPE_LEFT = "wipe_left"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


class TextAnimation(str, Enum):
    """Available text overlay animations."""

    NONE = "none"
    FADE_IN = "fade_in"
    POP_IN = "pop_in"
    SLIDE_UP = "slide_up"
    TYPEWRITER = "typewriter"


class TextPosition(str, Enum):
    """Available text positions."""

    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"
    LOWER_THIRD = "lower-third"


class BrandProfile(BaseModel):
    """Brand styling for the video."""

    primary_color: str | None = Field(
        default="#FF5733",
        description="Primary brand color in hex format",
    )
    font_family: str | None = Field(
        default="Inter",
        description="Font family for text overlays",
    )
    logo_url: str | None = Field(
        default=None,
        description="URL to brand logo",
    )


class AudioTrack(BaseModel):
    """Audio track configuration."""

    url: str = Field(..., description="URL to the audio file")
    volume: float = Field(default=0.8, ge=0.0, le=1.0, description="Audio volume (0-1)")
    fade_in_frames: int = Field(default=15, ge=0, description="Frames to fade in audio")
    fade_out_frames: int = Field(default=30, ge=0, description="Frames to fade out audio")


class TextOverlay(BaseModel):
    """Text overlay configuration for a segment."""

    text: str = Field(..., description="Text content to display")
    position: TextPosition = Field(default=TextPosition.CENTER, description="Text position")
    font_size: int = Field(default=48, ge=12, le=120, description="Font size in pixels")
    font_weight: str = Field(default="bold", description="Font weight: normal, bold, etc.")
    color: str = Field(default="#FFFFFF", description="Text color in hex format")
    background: str | None = Field(
        default="rgba(0,0,0,0.5)",
        description="Background color for text box",
    )
    animation: TextAnimation = Field(
        default=TextAnimation.NONE,
        description="Text entrance animation",
    )


class Transition(BaseModel):
    """Transition configuration."""

    type: TransitionType = Field(..., description="Type of transition")
    duration_frames: int = Field(default=0, ge=0, description="Duration in frames")


class VideoClipSource(BaseModel):
    """Source configuration for a video clip segment."""

    url: str = Field(..., description="URL to the source video file")
    start_time: float = Field(..., ge=0, description="Start time in seconds within source")
    end_time: float = Field(..., description="End time in seconds within source")


class GeneratedBRollSource(BaseModel):
    """Source configuration for AI-generated B-Roll."""

    url: str | None = Field(default=None, description="URL to generated clip (if available)")
    generation_prompt: str = Field(..., description="Prompt used to generate the B-Roll")
    regenerate_available: bool = Field(
        default=True,
        description="Whether user can regenerate this clip",
    )


class TextSlideContent(BaseModel):
    """Content for a text slide segment."""

    headline: str = Field(..., description="Main headline text")
    subheadline: str | None = Field(default=None, description="Optional subheadline")
    background_color: str = Field(default="#FF5733", description="Background color in hex")
    text_color: str = Field(default="#FFFFFF", description="Text color in hex")


class TimelineSegment(BaseModel):
    """A single segment in the video timeline."""

    id: str = Field(..., description="Unique segment identifier")
    type: SegmentType = Field(..., description="Type of segment")
    start_frame: int = Field(..., ge=0, description="Starting frame number")
    duration_frames: int = Field(..., gt=0, description="Duration in frames")

    # Source - one of these will be populated based on type
    source: VideoClipSource | None = Field(
        default=None,
        description="Source for video_clip type",
    )
    generated_source: GeneratedBRollSource | None = Field(
        default=None,
        description="Source for generated_broll type",
    )
    text_content: TextSlideContent | None = Field(
        default=None,
        description="Content for text_slide type",
    )

    # Visual overlays
    overlay: TextOverlay | None = Field(default=None, description="Text overlay on this segment")

    # Transitions
    transition_in: Transition | None = Field(default=None, description="Transition from previous")
    transition_out: Transition | None = Field(default=None, description="Transition to next")

    # Metadata from visual script
    beat_type: str | None = Field(default=None, description="Original beat type from script")
    slot_id: str | None = Field(default=None, description="Original slot ID from visual script")

    # Search metadata (for clip replacement UI)
    search_query: str | None = Field(
        default=None,
        description="Search query used to find this clip",
    )
    similarity_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Semantic similarity score (0-1)",
    )
    alternative_clips: list[dict] | None = Field(
        default=None,
        description="Alternative clip options for replacement",
    )


class RemotionPayload(BaseModel):
    """Complete payload for Remotion rendering."""

    composition_id: CompositionType = Field(
        default=CompositionType.VERTICAL,
        description="Remotion composition to use",
    )
    width: int = Field(default=1080, description="Video width in pixels")
    height: int = Field(default=1920, description="Video height in pixels")
    fps: int = Field(default=30, description="Frames per second")
    duration_in_frames: int = Field(..., description="Total duration in frames")

    # Props passed to Remotion composition
    project_id: uuid.UUID = Field(..., description="Project ID for reference")
    visual_script_id: uuid.UUID | None = Field(
        default=None,
        description="Visual script ID used to generate this payload",
    )
    brand_profile: BrandProfile | None = Field(
        default=None,
        description="Brand styling configuration",
    )
    audio_track: AudioTrack | None = Field(
        default=None,
        description="Background audio track",
    )
    timeline: list[TimelineSegment] = Field(
        default_factory=list,
        description="Ordered list of timeline segments",
    )

    # Metadata
    created_at: datetime | None = Field(default=None, description="When payload was created")
    version: int = Field(default=1, description="Payload version for edits")

    # Gap/issue tracking
    gaps: list[dict] | None = Field(
        default=None,
        description="Detected gaps where no suitable clip was found",
    )
    warnings: list[str] | None = Field(
        default=None,
        description="Warnings about the assembly (duration mismatches, etc.)",
    )


class DirectorAgentInput(BaseModel):
    """Input to the Director Agent."""

    project_id: uuid.UUID = Field(..., description="Project ID")
    visual_script_id: uuid.UUID = Field(..., description="Visual script to assemble")
    composition_type: CompositionType = Field(
        default=CompositionType.VERTICAL,
        description="Target aspect ratio",
    )
    min_similarity_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for clip selection",
    )
    gap_handling: str = Field(
        default="broll",
        description="How to handle gaps: 'broll' (generate), 'text_slide', or 'skip'",
    )
    audio_url: str | None = Field(
        default=None,
        description="Optional audio track URL",
    )


class DirectorAgentOutput(BaseModel):
    """Output from the Director Agent."""

    payload: RemotionPayload = Field(..., description="Generated Remotion payload")
    stats: dict = Field(
        default_factory=dict,
        description="Assembly statistics (clips used, gaps found, etc.)",
    )
    success: bool = Field(default=True, description="Whether assembly was successful")
    error_message: str | None = Field(
        default=None,
        description="Error message if assembly failed",
    )


class ClipSelectionResult(BaseModel):
    """Result of selecting a clip for a slot."""

    slot_id: str = Field(..., description="Visual script slot ID")
    selected: bool = Field(..., description="Whether a clip was selected")
    segment_id: uuid.UUID | None = Field(
        default=None,
        description="Selected segment ID",
    )
    source_file_url: str | None = Field(
        default=None,
        description="Source file URL",
    )
    timestamp_start: float | None = Field(
        default=None,
        description="Start time in source file",
    )
    timestamp_end: float | None = Field(
        default=None,
        description="End time in source file",
    )
    similarity_score: float | None = Field(
        default=None,
        description="Similarity score of selected clip",
    )
    gap_reason: str | None = Field(
        default=None,
        description="Reason why no clip was selected (if applicable)",
    )
    alternatives: list[dict] = Field(
        default_factory=list,
        description="Alternative clip options",
    )
