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
    BROLL_OVERLAY = "b_roll_overlay"
    TITLE_CARD = "title_card"


class OverlayPosition(str, Enum):
    """Position options for B-Roll overlay (PiP mode)."""

    FULL = "full"
    TOP_RIGHT = "top-right"
    BOTTOM_RIGHT = "bottom-right"
    TOP_LEFT = "top-left"
    BOTTOM_LEFT = "bottom-left"


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


class TitleAnimation(str, Enum):
    """Animation styles for title card text elements."""

    FADE_UP = "fade_up"
    FADE_DOWN = "fade_down"
    SCALE_IN = "scale_in"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    TYPEWRITER = "typewriter"
    NONE = "none"


class TitleCardLayout(str, Enum):
    """Layout styles for title cards."""

    CENTERED = "centered"
    LEFT_ALIGNED = "left_aligned"
    RIGHT_ALIGNED = "right_aligned"
    STACKED = "stacked"


class TitleCardLogoPosition(str, Enum):
    """Logo position options for title cards."""

    TOP = "top"
    BOTTOM = "bottom"
    BEHIND = "behind"


class BackgroundGradient(BaseModel):
    """Background gradient configuration."""

    start_color: str = Field(..., description="Gradient start color in hex")
    end_color: str = Field(..., description="Gradient end color in hex")
    angle: int = Field(default=135, ge=0, le=360, description="Gradient angle in degrees")


class TitleCardContent(BaseModel):
    """Content for a title card segment.

    Title cards are animated text screens with branding support,
    featuring headline + subheadline with professional animations.
    """

    headline: str = Field(..., description="Main headline text")
    subheadline: str | None = Field(default=None, description="Optional subheadline")
    tagline: str | None = Field(default=None, description="Optional tagline with accent")
    background_color: str = Field(
        default="#1a1a2e",
        description="Background color in hex (used if no gradient)",
    )
    text_color: str = Field(default="#FFFFFF", description="Text color in hex")
    accent_color: str | None = Field(
        default=None,
        description="Accent color for tagline and decorative elements",
    )
    animation: TitleAnimation = Field(
        default=TitleAnimation.FADE_UP,
        description="Animation style for text entrance",
    )
    layout: TitleCardLayout = Field(
        default=TitleCardLayout.CENTERED,
        description="Layout alignment for content",
    )
    show_logo: bool = Field(default=True, description="Whether to show brand logo")
    logo_position: TitleCardLogoPosition = Field(
        default=TitleCardLogoPosition.BOTTOM,
        description="Logo placement position",
    )
    background_gradient: BackgroundGradient | None = Field(
        default=None,
        description="Optional gradient background (overrides background_color)",
    )
    background_image_url: str | None = Field(
        default=None,
        description="Optional background image URL",
    )
    background_image_opacity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Opacity of background image (0-1)",
    )


class BRollOverlaySource(BaseModel):
    """Source configuration for B-Roll overlay (J-Cut/L-Cut editing).

    This enables professional video editing techniques:
    - J-Cut: Audio from the next clip starts before the visual cuts
    - L-Cut: Audio from the current clip continues over the next visual

    The main video provides continuous audio, while the overlay video
    appears/disappears with transitions, creating visual interest
    while maintaining audio continuity.
    """

    main_video: VideoClipSource = Field(
        ...,
        description="Main video that provides continuous audio track",
    )
    overlay_video: VideoClipSource = Field(
        ...,
        description="B-Roll video that overlays on top (video only, muted)",
    )
    overlay_start_offset_frames: int = Field(
        default=0,
        ge=0,
        description="When to start the overlay relative to segment start (in frames)",
    )
    overlay_duration_frames: int | None = Field(
        default=None,
        description="Duration of the overlay in frames (defaults to remaining segment duration)",
    )
    overlay_opacity: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Opacity of the overlay video (0-1)",
    )
    overlay_position: OverlayPosition = Field(
        default=OverlayPosition.FULL,
        description="Position of the overlay (full screen or PiP corners)",
    )
    overlay_scale: float = Field(
        default=1.0,
        ge=0.1,
        le=2.0,
        description="Scale factor for the overlay video",
    )
    overlay_transition_in: "Transition | None" = Field(
        default=None,
        description="Transition for the overlay appearing",
    )
    overlay_transition_out: "Transition | None" = Field(
        default=None,
        description="Transition for the overlay disappearing",
    )


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
    broll_overlay_source: BRollOverlaySource | None = Field(
        default=None,
        description="Source for b_roll_overlay type (J-Cut/L-Cut)",
    )
    title_card_content: "TitleCardContent | None" = Field(
        default=None,
        description="Content for title_card type (animated title screen)",
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
