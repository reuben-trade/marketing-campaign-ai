"""Director Converter - transforms DirectorLLMOutput to RemotionPayload."""

import logging
import uuid
from datetime import datetime, timezone

from app.models.user_video_segment import UserVideoSegment
from app.schemas.director_output import (
    AspectRatio,
    BRollOverlayEntry,
    DirectorLLMOutput,
    GeneratedBRollEntry,
    TextSlideEntry,
    TitleCardEntry,
    VideoClipEntry,
)
from app.schemas.remotion_payload import (
    BrandProfile,
    BRollOverlaySource,
    CompositionType,
    GeneratedBRollSource,
    RemotionPayload,
    SegmentType,
    TextAnimation,
    TextOverlay,
    TextPosition,
    TextSlideContent,
    TimelineSegment,
    TitleCardContent,
    Transition,
    TransitionType,
    VideoClipSource,
)

logger = logging.getLogger(__name__)


# Composition dimensions by type
COMPOSITION_DIMENSIONS = {
    CompositionType.VERTICAL: (1080, 1920),  # 9:16
    CompositionType.HORIZONTAL: (1920, 1080),  # 16:9
    CompositionType.SQUARE: (1080, 1080),  # 1:1
}

# Map aspect ratios to composition types
ASPECT_RATIO_TO_COMPOSITION = {
    AspectRatio.VERTICAL_9_16: CompositionType.VERTICAL,
    AspectRatio.HORIZONTAL_16_9: CompositionType.HORIZONTAL,
    AspectRatio.SQUARE_1_1: CompositionType.SQUARE,
}


class DirectorConverter:
    """Converts DirectorLLMOutput to RemotionPayload.

    The Director LLM outputs a timeline with times in SECONDS.
    This converter transforms it to the frame-based RemotionPayload
    that Remotion uses for rendering.
    """

    DEFAULT_FPS = 30

    def __init__(self, fps: int = DEFAULT_FPS):
        """Initialize converter with target FPS."""
        self.fps = fps

    def seconds_to_frames(self, seconds: float) -> int:
        """Convert seconds to frames."""
        return int(round(seconds * self.fps))

    def convert(
        self,
        llm_output: DirectorLLMOutput,
        project_id: uuid.UUID,
        visual_script_id: uuid.UUID | None = None,
        segment_lookup: dict[str, UserVideoSegment] | None = None,
        file_url_lookup: dict[str, str] | None = None,
    ) -> RemotionPayload:
        """Convert DirectorLLMOutput to RemotionPayload.

        Args:
            llm_output: The LLM's output with seconds-based times
            project_id: Project ID for the payload
            visual_script_id: Optional visual script ID
            segment_lookup: Dict mapping segment IDs to UserVideoSegment objects
            file_url_lookup: Dict mapping segment IDs to source file URLs

        Returns:
            RemotionPayload ready for Remotion rendering
        """
        segment_lookup = segment_lookup or {}
        file_url_lookup = file_url_lookup or {}

        # Map aspect ratio to composition type
        composition_id = ASPECT_RATIO_TO_COMPOSITION.get(
            llm_output.video_settings.aspect_ratio, CompositionType.VERTICAL
        )

        # Get dimensions
        width, height = COMPOSITION_DIMENSIONS[composition_id]

        # Convert timeline entries
        timeline_segments: list[TimelineSegment] = []
        for i, entry in enumerate(llm_output.timeline):
            segment = self._convert_entry(
                entry=entry,
                index=i,
                segment_lookup=segment_lookup,
                file_url_lookup=file_url_lookup,
            )
            if segment:
                timeline_segments.append(segment)

        # Calculate total duration from timeline
        total_seconds = llm_output.get_total_duration()
        total_frames = self.seconds_to_frames(total_seconds)

        # Build brand profile
        brand_profile = None
        if llm_output.video_settings.primary_color or llm_output.video_settings.font_family:
            brand_profile = BrandProfile(
                primary_color=llm_output.video_settings.primary_color,
                font_family=llm_output.video_settings.font_family,
            )

        # Convert gaps to dict format for payload
        gaps = None
        if llm_output.gaps:
            gaps = [
                {
                    "gap_id": gap.gap_id,
                    "position_seconds": gap.position_seconds,
                    "duration_seconds": gap.duration_seconds,
                    "reason": gap.reason,
                    "beat_type": gap.beat_type,
                    "recommended_action": gap.recommended_action.value,
                    "broll_prompt": gap.broll_prompt,
                    "search_query_suggestion": gap.search_query_suggestion,
                }
                for gap in llm_output.gaps
            ]

        # Convert caption highlights to warnings/metadata
        warnings = None
        if llm_output.caption_highlights:
            # Store as metadata for the caption overlay component
            warnings = [
                f"Caption highlight: '{h.word}' (color: {h.highlight_color})"
                for h in llm_output.caption_highlights
            ]

        logger.info(
            f"Converted DirectorLLMOutput to RemotionPayload: "
            f"{len(timeline_segments)} segments, {total_seconds:.1f}s duration, "
            f"{len(llm_output.gaps)} gaps"
        )

        return RemotionPayload(
            composition_id=composition_id,
            width=width,
            height=height,
            fps=self.fps,
            duration_in_frames=total_frames,
            project_id=project_id,
            visual_script_id=visual_script_id,
            brand_profile=brand_profile,
            timeline=timeline_segments,
            created_at=datetime.now(timezone.utc),
            version=1,
            gaps=gaps,
            warnings=warnings,
        )

    def _convert_entry(
        self,
        entry,
        index: int,
        segment_lookup: dict[str, UserVideoSegment],
        file_url_lookup: dict[str, str],
    ) -> TimelineSegment | None:
        """Convert a single timeline entry to a TimelineSegment."""
        start_frame = self.seconds_to_frames(entry.start_seconds)
        duration_frames = self.seconds_to_frames(entry.duration_seconds)

        if isinstance(entry, VideoClipEntry):
            return self._convert_video_clip(
                entry, index, start_frame, duration_frames, segment_lookup, file_url_lookup
            )
        elif isinstance(entry, BRollOverlayEntry):
            return self._convert_broll_overlay(
                entry, index, start_frame, duration_frames, segment_lookup, file_url_lookup
            )
        elif isinstance(entry, TitleCardEntry):
            return self._convert_title_card(entry, index, start_frame, duration_frames)
        elif isinstance(entry, TextSlideEntry):
            return self._convert_text_slide(entry, index, start_frame, duration_frames)
        elif isinstance(entry, GeneratedBRollEntry):
            return self._convert_generated_broll(entry, index, start_frame, duration_frames)

        logger.warning(f"Unknown entry type: {type(entry)}")
        return None

    def _convert_video_clip(
        self,
        entry: VideoClipEntry,
        index: int,
        start_frame: int,
        duration_frames: int,
        segment_lookup: dict[str, UserVideoSegment],
        file_url_lookup: dict[str, str],
    ) -> TimelineSegment:
        """Convert VideoClipEntry to TimelineSegment."""
        # Get source URL
        source_url = file_url_lookup.get(entry.segment_id, "")
        if not source_url and entry.segment_id in segment_lookup:
            seg = segment_lookup[entry.segment_id]
            source_url = seg.source_file_url or ""

        # Build text overlay if present
        overlay = None
        if entry.overlay_text:
            overlay = TextOverlay(
                text=entry.overlay_text,
                position=self._map_text_position(entry.overlay_position),
                animation=self._map_text_animation(entry.overlay_animation),
            )

        return TimelineSegment(
            id=f"segment_{index:02d}_video",
            type=SegmentType.VIDEO_CLIP,
            start_frame=start_frame,
            duration_frames=duration_frames,
            source=VideoClipSource(
                url=source_url,
                start_time=entry.source_start_seconds,
                end_time=entry.source_end_seconds,
            ),
            overlay=overlay,
            transition_in=self._map_transition(entry.transition_in),
            transition_out=self._map_transition(entry.transition_out),
            beat_type=entry.purpose,
        )

    def _convert_broll_overlay(
        self,
        entry: BRollOverlayEntry,
        index: int,
        start_frame: int,
        duration_frames: int,
        segment_lookup: dict[str, UserVideoSegment],
        file_url_lookup: dict[str, str],
    ) -> TimelineSegment:
        """Convert BRollOverlayEntry to TimelineSegment."""
        # Get main video URL
        main_url = file_url_lookup.get(entry.main_segment_id, "")
        if not main_url and entry.main_segment_id in segment_lookup:
            seg = segment_lookup[entry.main_segment_id]
            main_url = seg.source_file_url or ""

        # Get overlay video URL
        overlay_url = file_url_lookup.get(entry.overlay_segment_id, "")
        if not overlay_url and entry.overlay_segment_id in segment_lookup:
            seg = segment_lookup[entry.overlay_segment_id]
            overlay_url = seg.source_file_url or ""

        # Build text overlay if present
        overlay = None
        if entry.overlay_text:
            overlay = TextOverlay(
                text=entry.overlay_text,
                position=self._map_text_position(entry.overlay_text_position),
            )

        # Calculate overlay duration in frames
        overlay_duration_frames = None
        if entry.overlay_duration_seconds is not None:
            overlay_duration_frames = self.seconds_to_frames(entry.overlay_duration_seconds)

        return TimelineSegment(
            id=f"segment_{index:02d}_broll_overlay",
            type=SegmentType.BROLL_OVERLAY,
            start_frame=start_frame,
            duration_frames=duration_frames,
            broll_overlay_source=BRollOverlaySource(
                main_video=VideoClipSource(
                    url=main_url,
                    start_time=entry.main_source_start_seconds,
                    end_time=entry.main_source_end_seconds,
                ),
                overlay_video=VideoClipSource(
                    url=overlay_url,
                    start_time=entry.overlay_source_start_seconds,
                    end_time=entry.overlay_source_end_seconds,
                ),
                overlay_start_offset_frames=self.seconds_to_frames(
                    entry.overlay_start_offset_seconds
                ),
                overlay_duration_frames=overlay_duration_frames,
                overlay_opacity=entry.overlay_opacity,
                overlay_position=self._map_overlay_position(entry.overlay_position),
            ),
            overlay=overlay,
            transition_in=self._map_transition(entry.transition_in),
            transition_out=self._map_transition(entry.transition_out),
            beat_type=entry.purpose,
        )

    def _convert_title_card(
        self,
        entry: TitleCardEntry,
        index: int,
        start_frame: int,
        duration_frames: int,
    ) -> TimelineSegment:
        """Convert TitleCardEntry to TimelineSegment."""
        from app.schemas.remotion_payload import (
            TitleAnimation,
            TitleCardLayout,
        )

        # Map animation
        animation_map = {
            "fade_up": TitleAnimation.FADE_UP,
            "fade_down": TitleAnimation.FADE_DOWN,
            "scale_in": TitleAnimation.SCALE_IN,
            "slide_left": TitleAnimation.SLIDE_LEFT,
            "slide_right": TitleAnimation.SLIDE_RIGHT,
            "typewriter": TitleAnimation.TYPEWRITER,
            "none": TitleAnimation.NONE,
        }
        animation = animation_map.get(entry.animation.value, TitleAnimation.FADE_UP)

        # Map layout
        layout_map = {
            "centered": TitleCardLayout.CENTERED,
            "left_aligned": TitleCardLayout.LEFT_ALIGNED,
            "right_aligned": TitleCardLayout.RIGHT_ALIGNED,
            "stacked": TitleCardLayout.STACKED,
        }
        layout = layout_map.get(entry.layout.value, TitleCardLayout.CENTERED)

        return TimelineSegment(
            id=f"segment_{index:02d}_title_card",
            type=SegmentType.TITLE_CARD,
            start_frame=start_frame,
            duration_frames=duration_frames,
            title_card_content=TitleCardContent(
                headline=entry.headline,
                subheadline=entry.subheadline,
                tagline=entry.tagline,
                background_color=entry.background_color,
                text_color=entry.text_color,
                accent_color=entry.accent_color,
                animation=animation,
                layout=layout,
                show_logo=entry.show_logo,
            ),
            transition_in=self._map_transition(entry.transition_in),
            transition_out=self._map_transition(entry.transition_out),
            beat_type=entry.purpose,
        )

    def _convert_text_slide(
        self,
        entry: TextSlideEntry,
        index: int,
        start_frame: int,
        duration_frames: int,
    ) -> TimelineSegment:
        """Convert TextSlideEntry to TimelineSegment."""
        return TimelineSegment(
            id=f"segment_{index:02d}_text_slide",
            type=SegmentType.TEXT_SLIDE,
            start_frame=start_frame,
            duration_frames=duration_frames,
            text_content=TextSlideContent(
                headline=entry.headline,
                subheadline=entry.subheadline,
                background_color=entry.background_color,
                text_color=entry.text_color,
            ),
            transition_in=self._map_transition(entry.transition_in),
            transition_out=self._map_transition(entry.transition_out),
            beat_type=entry.purpose,
        )

    def _convert_generated_broll(
        self,
        entry: GeneratedBRollEntry,
        index: int,
        start_frame: int,
        duration_frames: int,
    ) -> TimelineSegment:
        """Convert GeneratedBRollEntry to TimelineSegment."""
        overlay = None
        if entry.overlay_text:
            overlay = TextOverlay(
                text=entry.overlay_text,
                position=self._map_text_position(entry.overlay_position),
            )

        return TimelineSegment(
            id=f"segment_{index:02d}_generated_broll",
            type=SegmentType.GENERATED_BROLL,
            start_frame=start_frame,
            duration_frames=duration_frames,
            generated_source=GeneratedBRollSource(
                url=None,  # Will be populated after Veo 2 generation
                generation_prompt=entry.generation_prompt,
                regenerate_available=True,
            ),
            overlay=overlay,
            transition_in=self._map_transition(entry.transition_in),
            transition_out=self._map_transition(entry.transition_out),
            beat_type=entry.purpose,
        )

    def _map_text_position(self, position) -> TextPosition:
        """Map director text position to Remotion TextPosition."""
        position_map = {
            "top": TextPosition.TOP,
            "center": TextPosition.CENTER,
            "bottom": TextPosition.BOTTOM,
            "lower-third": TextPosition.LOWER_THIRD,
        }
        return position_map.get(
            position.value if hasattr(position, "value") else position, TextPosition.CENTER
        )

    def _map_text_animation(self, animation) -> TextAnimation:
        """Map director text animation to Remotion TextAnimation."""
        animation_map = {
            "none": TextAnimation.NONE,
            "fade_in": TextAnimation.FADE_IN,
            "pop_in": TextAnimation.POP_IN,
            "slide_up": TextAnimation.SLIDE_UP,
            "typewriter": TextAnimation.TYPEWRITER,
        }
        return animation_map.get(
            animation.value if hasattr(animation, "value") else animation, TextAnimation.POP_IN
        )

    def _map_overlay_position(self, position):
        """Map director overlay position to Remotion OverlayPosition."""
        from app.schemas.remotion_payload import OverlayPosition

        position_map = {
            "full": OverlayPosition.FULL,
            "top-right": OverlayPosition.TOP_RIGHT,
            "bottom-right": OverlayPosition.BOTTOM_RIGHT,
            "top-left": OverlayPosition.TOP_LEFT,
            "bottom-left": OverlayPosition.BOTTOM_LEFT,
        }
        return position_map.get(
            position.value if hasattr(position, "value") else position, OverlayPosition.FULL
        )

    def _map_transition(self, transition_type) -> Transition | None:
        """Map director transition type to Remotion Transition."""
        if transition_type is None:
            return None

        type_value = transition_type.value if hasattr(transition_type, "value") else transition_type

        transition_map = {
            "cut": TransitionType.CUT,
            "dissolve": TransitionType.DISSOLVE,
            "fade": TransitionType.FADE,
            "wipe_right": TransitionType.WIPE_RIGHT,
            "wipe_left": TransitionType.WIPE_LEFT,
            "slide_up": TransitionType.SLIDE_UP,
            "slide_down": TransitionType.SLIDE_DOWN,
            "zoom_in": TransitionType.ZOOM_IN,
            "zoom_out": TransitionType.ZOOM_OUT,
        }

        remotion_type = transition_map.get(type_value, TransitionType.CUT)

        # Cuts have 0 duration, others have default 10 frames
        duration_frames = 0 if remotion_type == TransitionType.CUT else 10

        return Transition(type=remotion_type, duration_frames=duration_frames)
