"""Tests for Director Converter - transforms DirectorLLMOutput to RemotionPayload."""

import uuid

import pytest

from app.schemas.director_output import (
    AspectRatio,
    BRollOverlayEntry,
    CaptionHighlight,
    DirectorLLMOutput,
    DirectorVideoSettings,
    GapHandlingOption,
    GapRecommendation,
    GeneratedBRollEntry,
    OverlayPosition,
    TextSlideEntry,
    TitleCardAnimation,
    TitleCardEntry,
    TitleCardLayout,
    TransitionType,
    VideoClipEntry,
)
from app.schemas.remotion_payload import (
    CompositionType,
    SegmentType,
)
from app.services.director_converter import DirectorConverter


class TestDirectorConverter:
    """Tests for DirectorConverter class."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return DirectorConverter(fps=30)

    @pytest.fixture
    def project_id(self):
        """Create a test project ID."""
        return uuid.uuid4()

    def test_seconds_to_frames(self, converter):
        """Test seconds to frames conversion."""
        assert converter.seconds_to_frames(1.0) == 30
        assert converter.seconds_to_frames(0.5) == 15
        assert converter.seconds_to_frames(3.5) == 105
        assert converter.seconds_to_frames(0) == 0

    def test_seconds_to_frames_rounding(self, converter):
        """Test frames are rounded correctly."""
        # 0.33s * 30fps = 9.9 -> rounds to 10
        assert converter.seconds_to_frames(0.33) == 10
        # 0.34s * 30fps = 10.2 -> rounds to 10
        assert converter.seconds_to_frames(0.34) == 10

    def test_convert_minimal_output(self, converter, project_id):
        """Test conversion of minimal valid output."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                VideoClipEntry(
                    start_seconds=0,
                    duration_seconds=5,
                    purpose="Hook",
                    segment_id="clip-1",
                    source_start_seconds=0,
                    source_end_seconds=5,
                ),
            ],
        )

        payload = converter.convert(llm_output, project_id)

        assert payload.project_id == project_id
        assert payload.composition_id == CompositionType.VERTICAL
        assert payload.fps == 30
        assert len(payload.timeline) == 1
        assert payload.timeline[0].type == SegmentType.VIDEO_CLIP

    def test_convert_aspect_ratio_mapping(self, converter, project_id):
        """Test aspect ratio to composition type mapping."""
        test_cases = [
            (AspectRatio.VERTICAL_9_16, CompositionType.VERTICAL, 1080, 1920),
            (AspectRatio.HORIZONTAL_16_9, CompositionType.HORIZONTAL, 1920, 1080),
            (AspectRatio.SQUARE_1_1, CompositionType.SQUARE, 1080, 1080),
        ]

        for aspect_ratio, expected_comp, expected_width, expected_height in test_cases:
            llm_output = DirectorLLMOutput(
                video_settings=DirectorVideoSettings(
                    target_duration_seconds=30,
                    aspect_ratio=aspect_ratio,
                ),
                timeline=[
                    VideoClipEntry(
                        start_seconds=0,
                        duration_seconds=5,
                        purpose="Test",
                        segment_id="clip-1",
                        source_start_seconds=0,
                        source_end_seconds=5,
                    ),
                ],
            )
            payload = converter.convert(llm_output, project_id)
            assert payload.composition_id == expected_comp
            assert payload.width == expected_width
            assert payload.height == expected_height

    def test_convert_video_clip_entry(self, converter, project_id):
        """Test conversion of VideoClipEntry."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                VideoClipEntry(
                    start_seconds=0,
                    duration_seconds=4,
                    purpose="Hook with overlay",
                    segment_id="clip-123",
                    source_start_seconds=5.5,
                    source_end_seconds=9.5,
                    overlay_text="WATCH THIS",
                    transition_out=TransitionType.FADE,
                ),
            ],
        )

        # Create mock file URL lookup
        file_url_lookup = {"clip-123": "https://example.com/video.mp4"}

        payload = converter.convert(llm_output, project_id, file_url_lookup=file_url_lookup)

        segment = payload.timeline[0]
        assert segment.type == SegmentType.VIDEO_CLIP
        assert segment.start_frame == 0
        assert segment.duration_frames == 120  # 4s * 30fps
        assert segment.source.url == "https://example.com/video.mp4"
        assert segment.source.start_time == 5.5
        assert segment.source.end_time == 9.5
        assert segment.overlay.text == "WATCH THIS"
        assert segment.beat_type == "Hook with overlay"

    def test_convert_broll_overlay_entry(self, converter, project_id):
        """Test conversion of BRollOverlayEntry."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                BRollOverlayEntry(
                    start_seconds=0,
                    duration_seconds=5,
                    purpose="Visual variety",
                    main_segment_id="main-clip",
                    main_source_start_seconds=10,
                    main_source_end_seconds=15,
                    overlay_segment_id="overlay-clip",
                    overlay_source_start_seconds=0,
                    overlay_source_end_seconds=5,
                    overlay_position=OverlayPosition.BOTTOM_RIGHT,
                    overlay_opacity=0.8,
                ),
            ],
        )

        file_url_lookup = {
            "main-clip": "https://example.com/main.mp4",
            "overlay-clip": "https://example.com/overlay.mp4",
        }

        payload = converter.convert(llm_output, project_id, file_url_lookup=file_url_lookup)

        segment = payload.timeline[0]
        assert segment.type == SegmentType.BROLL_OVERLAY
        assert segment.broll_overlay_source.main_video.url == "https://example.com/main.mp4"
        assert segment.broll_overlay_source.overlay_video.url == "https://example.com/overlay.mp4"
        assert segment.broll_overlay_source.overlay_opacity == 0.8

    def test_convert_title_card_entry(self, converter, project_id):
        """Test conversion of TitleCardEntry."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                TitleCardEntry(
                    start_seconds=0,
                    duration_seconds=3,
                    purpose="Opening brand",
                    headline="SUMMER SALE",
                    subheadline="Up to 70% off",
                    tagline="Limited time only",
                    animation=TitleCardAnimation.SCALE_IN,
                    layout=TitleCardLayout.CENTERED,
                    background_color="#1a1a2e",
                    text_color="#FFFFFF",
                    show_logo=True,
                ),
            ],
        )

        payload = converter.convert(llm_output, project_id)

        segment = payload.timeline[0]
        assert segment.type == SegmentType.TITLE_CARD
        assert segment.title_card_content.headline == "SUMMER SALE"
        assert segment.title_card_content.subheadline == "Up to 70% off"
        assert segment.title_card_content.tagline == "Limited time only"
        assert segment.title_card_content.show_logo is True

    def test_convert_text_slide_entry(self, converter, project_id):
        """Test conversion of TextSlideEntry."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                TextSlideEntry(
                    start_seconds=0,
                    duration_seconds=2.5,
                    purpose="Key statistic",
                    headline="10,000+ Happy Customers",
                    subheadline="And counting!",
                    background_color="#FF5733",
                ),
            ],
        )

        payload = converter.convert(llm_output, project_id)

        segment = payload.timeline[0]
        assert segment.type == SegmentType.TEXT_SLIDE
        assert segment.start_frame == 0
        assert segment.duration_frames == 75  # 2.5s * 30fps
        assert segment.text_content.headline == "10,000+ Happy Customers"
        assert segment.text_content.background_color == "#FF5733"

    def test_convert_generated_broll_entry(self, converter, project_id):
        """Test conversion of GeneratedBRollEntry."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                GeneratedBRollEntry(
                    start_seconds=0,
                    duration_seconds=3,
                    purpose="Fill testimonial gap",
                    generation_prompt="Happy diverse customers smiling, bright natural lighting",
                    overlay_text="Real Results",
                ),
            ],
        )

        payload = converter.convert(llm_output, project_id)

        segment = payload.timeline[0]
        assert segment.type == SegmentType.GENERATED_BROLL
        assert (
            segment.generated_source.generation_prompt
            == "Happy diverse customers smiling, bright natural lighting"
        )
        assert segment.generated_source.url is None  # Not yet generated
        assert segment.generated_source.regenerate_available is True
        assert segment.overlay.text == "Real Results"

    def test_convert_multiple_entries(self, converter, project_id):
        """Test conversion of timeline with multiple entry types."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                TitleCardEntry(
                    start_seconds=0,
                    duration_seconds=2,
                    purpose="Brand intro",
                    headline="ACME Corp",
                ),
                VideoClipEntry(
                    start_seconds=2,
                    duration_seconds=5,
                    purpose="Hook",
                    segment_id="clip-1",
                    source_start_seconds=0,
                    source_end_seconds=5,
                ),
                TextSlideEntry(
                    start_seconds=7,
                    duration_seconds=3,
                    purpose="CTA",
                    headline="Shop Now!",
                ),
            ],
        )

        payload = converter.convert(llm_output, project_id)

        assert len(payload.timeline) == 3
        assert payload.timeline[0].type == SegmentType.TITLE_CARD
        assert payload.timeline[0].start_frame == 0
        assert payload.timeline[1].type == SegmentType.VIDEO_CLIP
        assert payload.timeline[1].start_frame == 60  # 2s * 30fps
        assert payload.timeline[2].type == SegmentType.TEXT_SLIDE
        assert payload.timeline[2].start_frame == 210  # 7s * 30fps

    def test_convert_gaps(self, converter, project_id):
        """Test conversion of gap recommendations."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                VideoClipEntry(
                    start_seconds=0,
                    duration_seconds=5,
                    purpose="Hook",
                    segment_id="clip-1",
                    source_start_seconds=0,
                    source_end_seconds=5,
                ),
            ],
            gaps=[
                GapRecommendation(
                    gap_id="gap-1",
                    position_seconds=10,
                    duration_seconds=3,
                    reason="No testimonial available",
                    beat_type="testimonial",
                    recommended_action=GapHandlingOption.GENERATE_BROLL,
                    broll_prompt="Customer testimonial style footage",
                ),
                GapRecommendation(
                    gap_id="gap-2",
                    position_seconds=20,
                    duration_seconds=2,
                    reason="Need product close-up",
                    recommended_action=GapHandlingOption.UPLOAD_CLIP,
                    search_query_suggestion="product close-up shot",
                ),
            ],
        )

        payload = converter.convert(llm_output, project_id)

        assert payload.gaps is not None
        assert len(payload.gaps) == 2
        assert payload.gaps[0]["gap_id"] == "gap-1"
        assert payload.gaps[0]["recommended_action"] == "generate_broll"
        assert payload.gaps[0]["broll_prompt"] == "Customer testimonial style footage"
        assert payload.gaps[1]["recommended_action"] == "upload_clip"

    def test_convert_brand_profile(self, converter, project_id):
        """Test brand profile is created from video settings."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(
                target_duration_seconds=30,
                primary_color="#FF5733",
                font_family="Montserrat",
            ),
            timeline=[
                VideoClipEntry(
                    start_seconds=0,
                    duration_seconds=5,
                    purpose="Hook",
                    segment_id="clip-1",
                    source_start_seconds=0,
                    source_end_seconds=5,
                ),
            ],
        )

        payload = converter.convert(llm_output, project_id)

        assert payload.brand_profile is not None
        assert payload.brand_profile.primary_color == "#FF5733"
        assert payload.brand_profile.font_family == "Montserrat"

    def test_convert_total_duration(self, converter, project_id):
        """Test total duration is calculated correctly."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                VideoClipEntry(
                    start_seconds=0,
                    duration_seconds=10,
                    purpose="Part 1",
                    segment_id="clip-1",
                    source_start_seconds=0,
                    source_end_seconds=10,
                ),
                VideoClipEntry(
                    start_seconds=10,
                    duration_seconds=8,
                    purpose="Part 2",
                    segment_id="clip-2",
                    source_start_seconds=0,
                    source_end_seconds=8,
                ),
            ],
        )

        payload = converter.convert(llm_output, project_id)

        # Total should be 18 seconds = 540 frames
        assert payload.duration_in_frames == 540

    def test_convert_with_visual_script_id(self, converter, project_id):
        """Test visual_script_id is passed through."""
        visual_script_id = uuid.uuid4()
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                VideoClipEntry(
                    start_seconds=0,
                    duration_seconds=5,
                    purpose="Hook",
                    segment_id="clip-1",
                    source_start_seconds=0,
                    source_end_seconds=5,
                ),
            ],
        )

        payload = converter.convert(llm_output, project_id, visual_script_id=visual_script_id)

        assert payload.visual_script_id == visual_script_id

    def test_convert_caption_highlights_to_warnings(self, converter, project_id):
        """Test caption highlights are stored in warnings."""
        llm_output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                VideoClipEntry(
                    start_seconds=0,
                    duration_seconds=5,
                    purpose="Hook",
                    segment_id="clip-1",
                    source_start_seconds=0,
                    source_end_seconds=5,
                ),
            ],
            caption_highlights=[
                CaptionHighlight(word="FREE", highlight_color="#FFD700"),
                CaptionHighlight(word="guaranteed", highlight_color="#00FF00"),
            ],
        )

        payload = converter.convert(llm_output, project_id)

        # Caption highlights are stored in warnings for now
        assert payload.warnings is not None
        assert len(payload.warnings) == 2
        assert "FREE" in payload.warnings[0]
        assert "guaranteed" in payload.warnings[1]


class TestDirectorConverterCustomFPS:
    """Test DirectorConverter with custom FPS."""

    def test_custom_fps(self):
        """Test converter with 60fps."""
        converter = DirectorConverter(fps=60)
        assert converter.seconds_to_frames(1.0) == 60
        assert converter.seconds_to_frames(0.5) == 30

    def test_24fps_film(self):
        """Test converter with 24fps (film standard)."""
        converter = DirectorConverter(fps=24)
        assert converter.seconds_to_frames(1.0) == 24
        assert converter.seconds_to_frames(2.5) == 60
