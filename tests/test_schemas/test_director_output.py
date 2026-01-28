"""Tests for Director LLM Output schema."""

import json

import pytest
from pydantic import ValidationError

from app.schemas.director_output import (
    AspectRatio,
    BRollOverlayEntry,
    CaptionHighlight,
    DirectorLLMOutput,
    DirectorThinkingTrace,
    DirectorVideoSettings,
    GapHandlingOption,
    GapRecommendation,
    GeneratedBRollEntry,
    MusicMood,
    TextSlideEntry,
    TimelineEntryType,
    TitleCardEntry,
    VideoClipEntry,
)


class TestDirectorVideoSettings:
    """Tests for DirectorVideoSettings schema."""

    def test_default_values(self):
        """Test default values are set correctly."""
        settings = DirectorVideoSettings(target_duration_seconds=30)
        assert settings.aspect_ratio == AspectRatio.VERTICAL_9_16
        assert settings.target_duration_seconds == 30
        assert settings.music_mood is None
        assert settings.primary_color is None

    def test_all_fields(self):
        """Test all fields can be set."""
        settings = DirectorVideoSettings(
            aspect_ratio=AspectRatio.HORIZONTAL_16_9,
            target_duration_seconds=45,
            music_mood=MusicMood.UPBEAT,
            primary_color="#FF5733",
            font_family="Inter",
        )
        assert settings.aspect_ratio == AspectRatio.HORIZONTAL_16_9
        assert settings.target_duration_seconds == 45
        assert settings.music_mood == MusicMood.UPBEAT

    def test_duration_validation_min(self):
        """Test minimum duration validation."""
        with pytest.raises(ValidationError) as exc_info:
            DirectorVideoSettings(target_duration_seconds=10)
        assert "greater than or equal to 15" in str(exc_info.value)

    def test_duration_validation_max(self):
        """Test maximum duration validation."""
        with pytest.raises(ValidationError) as exc_info:
            DirectorVideoSettings(target_duration_seconds=90)
        assert "less than or equal to 60" in str(exc_info.value)


class TestVideoClipEntry:
    """Tests for VideoClipEntry schema."""

    def test_valid_entry(self):
        """Test valid video clip entry."""
        entry = VideoClipEntry(
            start_seconds=0,
            duration_seconds=3.5,
            purpose="Hook - high attention score",
            segment_id="abc-123",
            source_start_seconds=5.0,
            source_end_seconds=8.5,
        )
        assert entry.entry_type == TimelineEntryType.VIDEO_CLIP
        assert entry.start_seconds == 0
        assert entry.duration_seconds == 3.5
        assert entry.segment_id == "abc-123"

    def test_with_overlay(self):
        """Test video clip with text overlay."""
        entry = VideoClipEntry(
            start_seconds=0,
            duration_seconds=4,
            purpose="Product showcase",
            segment_id="def-456",
            source_start_seconds=0,
            source_end_seconds=4,
            overlay_text="50% OFF TODAY",
        )
        assert entry.overlay_text == "50% OFF TODAY"

    def test_duration_max_validation(self):
        """Test maximum duration validation (10s)."""
        with pytest.raises(ValidationError) as exc_info:
            VideoClipEntry(
                start_seconds=0,
                duration_seconds=15,  # Too long
                purpose="Test",
                segment_id="test",
                source_start_seconds=0,
                source_end_seconds=15,
            )
        assert "less than or equal to 10" in str(exc_info.value)


class TestBRollOverlayEntry:
    """Tests for BRollOverlayEntry schema."""

    def test_valid_entry(self):
        """Test valid B-roll overlay entry."""
        entry = BRollOverlayEntry(
            start_seconds=5,
            duration_seconds=3,
            purpose="Visual variety - product shot",
            main_segment_id="main-123",
            main_source_start_seconds=10,
            main_source_end_seconds=13,
            overlay_segment_id="overlay-456",
            overlay_source_start_seconds=0,
            overlay_source_end_seconds=3,
        )
        assert entry.entry_type == TimelineEntryType.BROLL_OVERLAY
        assert entry.main_segment_id == "main-123"
        assert entry.overlay_segment_id == "overlay-456"
        assert entry.overlay_opacity == 1.0  # default


class TestTitleCardEntry:
    """Tests for TitleCardEntry schema."""

    def test_valid_entry(self):
        """Test valid title card entry."""
        entry = TitleCardEntry(
            start_seconds=0,
            duration_seconds=2,
            purpose="Opening branding",
            headline="SUMMER SALE",
            subheadline="Up to 70% off",
        )
        assert entry.entry_type == TimelineEntryType.TITLE_CARD
        assert entry.headline == "SUMMER SALE"
        assert entry.show_logo is True  # default


class TestTextSlideEntry:
    """Tests for TextSlideEntry schema."""

    def test_valid_entry(self):
        """Test valid text slide entry."""
        entry = TextSlideEntry(
            start_seconds=10,
            duration_seconds=2.5,
            purpose="Key statistic",
            headline="10,000+ Happy Customers",
        )
        assert entry.entry_type == TimelineEntryType.TEXT_SLIDE


class TestGeneratedBRollEntry:
    """Tests for GeneratedBRollEntry schema."""

    def test_valid_entry(self):
        """Test valid generated B-roll entry."""
        entry = GeneratedBRollEntry(
            start_seconds=8,
            duration_seconds=2,
            purpose="Fill gap - no testimonial clip",
            generation_prompt="Happy customers smiling and waving, bright sunny day, diverse group",
        )
        assert entry.entry_type == TimelineEntryType.GENERATED_BROLL
        assert "Happy customers" in entry.generation_prompt


class TestGapRecommendation:
    """Tests for GapRecommendation schema."""

    def test_generate_broll_recommendation(self):
        """Test gap with generate_broll recommendation."""
        gap = GapRecommendation(
            gap_id="gap-1",
            position_seconds=15,
            duration_seconds=3,
            reason="No testimonial clip available",
            recommended_action=GapHandlingOption.GENERATE_BROLL,
            broll_prompt="Satisfied customer giving thumbs up",
        )
        assert gap.recommended_action == GapHandlingOption.GENERATE_BROLL
        assert gap.broll_prompt is not None

    def test_upload_clip_recommendation(self):
        """Test gap with upload_clip recommendation."""
        gap = GapRecommendation(
            gap_id="gap-2",
            position_seconds=25,
            duration_seconds=4,
            reason="Need CTA with specific product",
            recommended_action=GapHandlingOption.UPLOAD_CLIP,
            search_query_suggestion="product demo call to action",
        )
        assert gap.recommended_action == GapHandlingOption.UPLOAD_CLIP


class TestCaptionHighlight:
    """Tests for CaptionHighlight schema."""

    def test_valid_highlight(self):
        """Test valid caption highlight."""
        highlight = CaptionHighlight(
            word="FREE",
            highlight_color="#FFD700",
            is_power_word=True,
        )
        assert highlight.word == "FREE"
        assert highlight.is_power_word is True

    def test_default_color(self):
        """Test default highlight color."""
        highlight = CaptionHighlight(word="guaranteed")
        assert highlight.highlight_color == "#FFD700"


class TestDirectorThinkingTrace:
    """Tests for DirectorThinkingTrace schema."""

    def test_full_trace(self):
        """Test full thinking trace."""
        trace = DirectorThinkingTrace(
            hook_analysis="Clip 3 has attention_score 9, face + speech",
            story_arc="Hook -> Problem -> Solution -> CTA",
            pacing_decisions="Use B-roll at 8s to break up talking head",
            clip_selection_rationale=["Clip 3 for hook", "Clip 5 for CTA"],
            cta_strategy="Title card with Shop Now",
        )
        assert len(trace.clip_selection_rationale) == 2


class TestDirectorLLMOutput:
    """Tests for DirectorLLMOutput schema."""

    def test_minimal_valid_output(self):
        """Test minimal valid output."""
        output = DirectorLLMOutput(
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
        assert output.get_total_duration() == 5
        assert len(output.timeline) == 1

    def test_complete_output(self):
        """Test complete output with all fields."""
        output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(
                target_duration_seconds=30,
                aspect_ratio=AspectRatio.VERTICAL_9_16,
                music_mood=MusicMood.UPBEAT,
            ),
            timeline=[
                TitleCardEntry(
                    start_seconds=0,
                    duration_seconds=2,
                    purpose="Branding",
                    headline="ACME Corp",
                ),
                VideoClipEntry(
                    start_seconds=2,
                    duration_seconds=8,
                    purpose="Hook - high attention",
                    segment_id="clip-1",
                    source_start_seconds=5,
                    source_end_seconds=13,
                ),
                TextSlideEntry(
                    start_seconds=10,
                    duration_seconds=3,
                    purpose="Key stat",
                    headline="10,000+ Sales",
                ),
            ],
            gaps=[
                GapRecommendation(
                    gap_id="gap-1",
                    position_seconds=13,
                    duration_seconds=2,
                    reason="No CTA clip",
                    recommended_action=GapHandlingOption.GENERATE_BROLL,
                    broll_prompt="Call to action animation",
                ),
            ],
            caption_highlights=[
                CaptionHighlight(word="FREE"),
                CaptionHighlight(word="guaranteed"),
            ],
            thinking_trace=DirectorThinkingTrace(
                hook_analysis="Used clip-1 for attention_score 9",
            ),
        )
        assert output.get_total_duration() == 13
        assert len(output.gaps) == 1
        assert len(output.caption_highlights) == 2

    def test_timeline_must_start_at_zero(self):
        """Test timeline validation - must start at 0."""
        with pytest.raises(ValidationError) as exc_info:
            DirectorLLMOutput(
                video_settings=DirectorVideoSettings(target_duration_seconds=30),
                timeline=[
                    VideoClipEntry(
                        start_seconds=5,  # Should be 0
                        duration_seconds=5,
                        purpose="Hook",
                        segment_id="clip-1",
                        source_start_seconds=0,
                        source_end_seconds=5,
                    ),
                ],
            )
        assert "must start at 0" in str(exc_info.value)

    def test_empty_timeline_rejected(self):
        """Test empty timeline is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DirectorLLMOutput(
                video_settings=DirectorVideoSettings(target_duration_seconds=30),
                timeline=[],
            )
        assert "at least 1" in str(exc_info.value).lower()

    def test_json_serialization(self):
        """Test JSON serialization round-trip."""
        output = DirectorLLMOutput(
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
        # Serialize to JSON
        json_str = output.model_dump_json()
        data = json.loads(json_str)

        # Verify structure
        assert data["video_settings"]["target_duration_seconds"] == 30
        assert len(data["timeline"]) == 1
        assert data["timeline"][0]["entry_type"] == "video_clip"

    def test_json_schema_generation(self):
        """Test JSON schema can be generated for LLM."""
        schema = DirectorLLMOutput.model_json_schema()
        assert "video_settings" in schema["properties"]
        assert "timeline" in schema["properties"]
        assert "gaps" in schema["properties"]
        assert "caption_highlights" in schema["properties"]
