"""Director LLM Output Schema - what the Director AI produces.

This schema is optimized for LLM output (uses seconds, human-readable).
It gets converted to RemotionPayload for rendering.
"""

import uuid
from enum import Enum

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Video Settings Enums
# =============================================================================


class AspectRatio(str, Enum):
    """Target aspect ratio for the video."""

    VERTICAL_9_16 = "9:16"  # Stories/Reels/TikTok
    HORIZONTAL_16_9 = "16:9"  # YouTube/Facebook Feed
    SQUARE_1_1 = "1:1"  # Instagram Feed


class MusicMood(str, Enum):
    """Mood for background music selection."""

    UPBEAT = "upbeat"
    INSPIRING = "inspiring"
    CALM = "calm"
    URGENT = "urgent"
    DRAMATIC = "dramatic"
    PLAYFUL = "playful"
    LOFI = "lo-fi"
    CORPORATE = "corporate"


# =============================================================================
# Timeline Entry Enums
# =============================================================================


class TimelineEntryType(str, Enum):
    """Types of entries in the director's timeline."""

    VIDEO_CLIP = "video_clip"
    BROLL_OVERLAY = "broll_overlay"
    TITLE_CARD = "title_card"
    TEXT_SLIDE = "text_slide"
    GENERATED_BROLL = "generated_broll"


class OverlayPosition(str, Enum):
    """Position for B-Roll overlay (PiP mode)."""

    FULL = "full"
    TOP_RIGHT = "top-right"
    BOTTOM_RIGHT = "bottom-right"
    TOP_LEFT = "top-left"
    BOTTOM_LEFT = "bottom-left"


class TextPosition(str, Enum):
    """Position for text overlays."""

    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"
    LOWER_THIRD = "lower-third"


class TextAnimation(str, Enum):
    """Animation for text overlays."""

    NONE = "none"
    FADE_IN = "fade_in"
    POP_IN = "pop_in"
    SLIDE_UP = "slide_up"
    TYPEWRITER = "typewriter"


class TitleCardAnimation(str, Enum):
    """Animation styles for title cards."""

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


class TransitionType(str, Enum):
    """Transition types between segments."""

    CUT = "cut"
    DISSOLVE = "dissolve"
    FADE = "fade"
    WIPE_RIGHT = "wipe_right"
    WIPE_LEFT = "wipe_left"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


# =============================================================================
# Gap Handling
# =============================================================================


class GapHandlingOption(str, Enum):
    """Options for handling content gaps."""

    GENERATE_BROLL = "generate_broll"
    UPLOAD_CLIP = "upload_clip"
    PROCEED_WITHOUT = "proceed_without"


class GapRecommendation(BaseModel):
    """A gap in the timeline with resolution options."""

    gap_id: str = Field(..., description="Unique ID for this gap")
    position_seconds: float = Field(..., ge=0, description="Where the gap occurs in the timeline")
    duration_seconds: float = Field(..., gt=0, description="How long the gap is")
    reason: str = Field(
        ..., description="Why there's a gap (e.g., 'No clip matches hook requirement')"
    )
    beat_type: str | None = Field(default=None, description="What type of content is missing")

    # Recommendations
    recommended_action: GapHandlingOption = Field(
        default=GapHandlingOption.GENERATE_BROLL,
        description="Recommended way to handle this gap",
    )
    broll_prompt: str | None = Field(
        default=None,
        description="Suggested Veo 2 prompt if generate_broll is chosen",
    )
    search_query_suggestion: str | None = Field(
        default=None,
        description="Alternative search query for finding clips",
    )


# =============================================================================
# Caption Highlights
# =============================================================================


class CaptionHighlight(BaseModel):
    """Words to highlight in the caption overlay."""

    word: str = Field(..., description="The word to highlight (case-insensitive matching)")
    highlight_color: str = Field(
        default="#FFD700",
        description="Highlight color in hex format",
    )
    is_power_word: bool = Field(
        default=False,
        description="Whether this is a power word (free, guaranteed, etc.)",
    )


# =============================================================================
# Video Settings
# =============================================================================


class DirectorVideoSettings(BaseModel):
    """Video-level settings decided by the Director."""

    aspect_ratio: AspectRatio = Field(
        default=AspectRatio.VERTICAL_9_16,
        description="Target aspect ratio for the final video",
    )
    target_duration_seconds: float = Field(
        ...,
        ge=15.0,
        le=60.0,
        description="Target total duration (15-60 seconds)",
    )
    music_mood: MusicMood | None = Field(
        default=None,
        description="Suggested mood for background music",
    )
    primary_color: str | None = Field(
        default=None,
        description="Primary brand color (hex format)",
    )
    font_family: str | None = Field(
        default=None,
        description="Font family for text overlays",
    )


# =============================================================================
# Timeline Entry Types (all use SECONDS for times)
# =============================================================================


class BaseTimelineEntry(BaseModel):
    """Base class for all timeline entries."""

    entry_type: TimelineEntryType
    start_seconds: float = Field(..., ge=0, description="Start time in seconds")
    duration_seconds: float = Field(
        ...,
        gt=0,
        le=10,
        description="Duration in seconds (max 10s per segment)",
    )
    purpose: str = Field(
        ...,
        description="Why this segment was chosen (for debugging/explanation)",
    )
    transition_in: TransitionType = Field(default=TransitionType.CUT)
    transition_out: TransitionType = Field(default=TransitionType.CUT)


class VideoClipEntry(BaseTimelineEntry):
    """Main footage playback with time slicing."""

    entry_type: TimelineEntryType = TimelineEntryType.VIDEO_CLIP

    # Source clip reference
    segment_id: str = Field(..., description="UUID of the UserVideoSegment to use")
    source_start_seconds: float = Field(..., ge=0, description="Start time within the source video")
    source_end_seconds: float = Field(..., description="End time within the source video")

    # Optional text overlay
    overlay_text: str | None = Field(default=None, description="Text to show over video")
    overlay_position: TextPosition = Field(default=TextPosition.CENTER)
    overlay_animation: TextAnimation = Field(default=TextAnimation.POP_IN)


class BRollOverlayEntry(BaseTimelineEntry):
    """B-Roll overlay for J-cut/L-cut editing.

    Main video provides audio, overlay video is muted.
    This creates professional audio continuity.
    """

    entry_type: TimelineEntryType = TimelineEntryType.BROLL_OVERLAY

    # Main video (provides audio)
    main_segment_id: str = Field(..., description="UUID of main video segment (provides audio)")
    main_source_start_seconds: float = Field(..., ge=0)
    main_source_end_seconds: float = Field(...)

    # Overlay video (muted, video only)
    overlay_segment_id: str = Field(..., description="UUID of overlay video segment (muted)")
    overlay_source_start_seconds: float = Field(..., ge=0)
    overlay_source_end_seconds: float = Field(...)

    # Overlay timing (relative to segment start)
    overlay_start_offset_seconds: float = Field(
        default=0,
        ge=0,
        description="When overlay starts relative to segment start",
    )
    overlay_duration_seconds: float | None = Field(
        default=None,
        description="Duration of overlay (defaults to remaining segment)",
    )

    # Overlay style
    overlay_position: OverlayPosition = Field(default=OverlayPosition.FULL)
    overlay_opacity: float = Field(default=1.0, ge=0.0, le=1.0)

    # Text overlay (optional)
    overlay_text: str | None = Field(default=None)
    overlay_text_position: TextPosition = Field(default=TextPosition.CENTER)


class TitleCardEntry(BaseTimelineEntry):
    """Animated title card with branding."""

    entry_type: TimelineEntryType = TimelineEntryType.TITLE_CARD

    headline: str = Field(..., description="Main headline text")
    subheadline: str | None = Field(default=None, description="Optional subheadline")
    tagline: str | None = Field(default=None, description="Optional tagline with accent")

    background_color: str = Field(default="#1a1a2e", description="Background color (hex)")
    text_color: str = Field(default="#FFFFFF", description="Text color (hex)")
    accent_color: str | None = Field(default=None, description="Accent for tagline")

    animation: TitleCardAnimation = Field(default=TitleCardAnimation.FADE_UP)
    layout: TitleCardLayout = Field(default=TitleCardLayout.CENTERED)
    show_logo: bool = Field(default=True)


class TextSlideEntry(BaseTimelineEntry):
    """Clean text slide with spring animations."""

    entry_type: TimelineEntryType = TimelineEntryType.TEXT_SLIDE

    headline: str = Field(..., description="Main text")
    subheadline: str | None = Field(default=None)
    background_color: str = Field(default="#1a1a2e")
    text_color: str = Field(default="#FFFFFF")


class GeneratedBRollEntry(BaseTimelineEntry):
    """Placeholder for AI-generated B-Roll (Veo 2)."""

    entry_type: TimelineEntryType = TimelineEntryType.GENERATED_BROLL

    generation_prompt: str = Field(..., description="Prompt for Veo 2 B-Roll generation")
    overlay_text: str | None = Field(default=None)
    overlay_position: TextPosition = Field(default=TextPosition.CENTER)


# Union type for all timeline entries
TimelineEntry = (
    VideoClipEntry | BRollOverlayEntry | TitleCardEntry | TextSlideEntry | GeneratedBRollEntry
)


# =============================================================================
# Director Thinking Trace
# =============================================================================


class DirectorThinkingTrace(BaseModel):
    """Extended thinking trace from the Director.

    Captures the Director's creative reasoning for debugging and explanation.
    """

    hook_analysis: str | None = Field(
        default=None,
        description="Analysis of which clip makes the best hook and why",
    )
    story_arc: str | None = Field(
        default=None,
        description="How the clips map to the narrative arc",
    )
    pacing_decisions: str | None = Field(
        default=None,
        description="Pacing and rhythm decisions",
    )
    clip_selection_rationale: list[str] = Field(
        default_factory=list,
        description="Why each clip was selected",
    )
    cta_strategy: str | None = Field(
        default=None,
        description="CTA placement and messaging strategy",
    )
    gaps_identified: list[str] = Field(
        default_factory=list,
        description="Missing content that was identified",
    )


# =============================================================================
# Main Director Output
# =============================================================================


class DirectorLLMOutput(BaseModel):
    """Complete output from the Director LLM.

    This schema is what the LLM produces. It uses SECONDS for all times
    and is then converted to RemotionPayload (which uses frames).
    """

    # Video settings
    video_settings: DirectorVideoSettings

    # Main timeline (ordered list of entries)
    timeline: list[TimelineEntry] = Field(
        ...,
        min_length=1,
        description="Ordered timeline of segments. Must start at 0 seconds.",
    )

    # Gap handling
    gaps: list[GapRecommendation] = Field(
        default_factory=list,
        description="Gaps that need resolution (empty if all slots filled)",
    )

    # Caption highlights
    caption_highlights: list[CaptionHighlight] = Field(
        default_factory=list,
        description="Words to highlight in captions (from SRT)",
    )

    # Extended thinking (optional)
    thinking_trace: DirectorThinkingTrace | None = Field(
        default=None,
        description="Director's reasoning trace (for debugging/explanation)",
    )

    @field_validator("timeline")
    @classmethod
    def validate_timeline_starts_at_zero(cls, v: list[TimelineEntry]) -> list[TimelineEntry]:
        """Ensure timeline starts at 0 seconds."""
        if not v:
            raise ValueError("Timeline cannot be empty")
        if v[0].start_seconds != 0:
            raise ValueError(f"Timeline must start at 0 seconds, got {v[0].start_seconds}")
        return v

    @field_validator("timeline")
    @classmethod
    def validate_timeline_continuity(cls, v: list[TimelineEntry]) -> list[TimelineEntry]:
        """Check for gaps between segments (warning only, not error)."""
        for i in range(1, len(v)):
            prev_end = v[i - 1].start_seconds + v[i - 1].duration_seconds
            curr_start = v[i].start_seconds
            gap = curr_start - prev_end
            if gap > 0.1:  # Allow 100ms tolerance for floating point
                # Log warning but don't fail - gaps are tracked separately
                pass
        return v

    def get_total_duration(self) -> float:
        """Calculate total duration from timeline entries."""
        if not self.timeline:
            return 0
        last_entry = self.timeline[-1]
        return last_entry.start_seconds + last_entry.duration_seconds


# =============================================================================
# Clip Inventory (input to Director)
# =============================================================================


class ClipInfo(BaseModel):
    """Information about an available clip for the Director."""

    id: str = Field(..., description="UUID of the UserVideoSegment")
    source_file_name: str | None = None
    timestamp_start: float
    timestamp_end: float
    duration_seconds: float

    # V2 Analysis fields
    visual_description: str | None = None
    section_type: str | None = None
    section_label: str | None = None
    attention_score: int | None = Field(None, ge=1, le=10)
    emotion_intensity: int | None = Field(None, ge=1, le=10)
    has_speech: bool = False
    keywords: list[str] = Field(default_factory=list)
    detailed_breakdown: str | None = None

    # Ordering
    segment_index: int = 0
    total_segments_in_source: int = 1


class DirectorInput(BaseModel):
    """Input data for the Director agent."""

    project_id: uuid.UUID
    available_clips: list[ClipInfo]
    target_duration_seconds: int = Field(default=30, ge=15, le=60)

    # Optional context
    visual_script: dict | None = Field(
        default=None,
        description="Visual script with slots to follow",
    )
    brand_profile: dict | None = Field(
        default=None,
        description="Brand colors, fonts, forbidden terms",
    )
    user_instructions: str | None = Field(
        default=None,
        description="User's creative direction",
    )
    srt_content: str | None = Field(
        default=None,
        description="Global SRT subtitles for caption highlighting",
    )
    inspiration_style: dict | None = Field(
        default=None,
        description="Pacing/style from competitor inspiration",
    )
