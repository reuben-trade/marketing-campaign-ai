"""Video analysis service using Google Gemini."""

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.schemas.ad import AdAnalysis, MarketingEffectiveness, VideoAnalysis
from app.schemas.ad_analysis import (
    AdCritique,
    AudioAnalysis,
    BrandElements,
    CopyAnalysis,
    EmotionalArc,
    EngagementPredictors,
    EnhancedAdAnalysisV2,
    EnhancedCinematicDetails,
    EnhancedNarrativeBeat,
    EnhancedRhetoricalAppeal,
    MusicAnalysis,
    PlatformOptimization,
    TextOverlay,
    ThumbStopAnalysis,
    VoiceAnalysis,
)
from app.utils.prompts import VIDEO_ANALYSIS_PROMPT_V2
from app.utils.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)


class VideoAnalysisError(Exception):
    """Exception raised when video analysis fails."""

    pass


class VideoAnalyzer:
    """Analyzes ad videos using Google Gemini."""

    def __init__(self) -> None:
        """Initialize the video analyzer."""
        settings = get_settings()
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model_name = "gemini-2.0-flash"
        self.storage = SupabaseStorage()

    def parse_analysis(self, raw_analysis: dict[str, Any]) -> AdAnalysis:
        """
        Parse raw analysis into an AdAnalysis schema.

        Args:
            raw_analysis: Raw analysis dictionary from the AI

        Returns:
            AdAnalysis object
        """
        effectiveness = raw_analysis.get("marketing_effectiveness", {})
        video_data = raw_analysis.get("video_analysis", {})

        video_analysis = None
        if video_data:
            video_analysis = VideoAnalysis(
                pacing=video_data.get("pacing", ""),
                audio_strategy=video_data.get("audio_strategy", ""),
                story_arc=video_data.get("story_arc", ""),
                caption_usage=video_data.get("caption_usage", ""),
                optimal_length=video_data.get("optimal_length", ""),
            )

        return AdAnalysis(
            summary=raw_analysis.get("summary", ""),
            insights=raw_analysis.get("insights", []),
            uvps=raw_analysis.get("uvps", []),
            ctas=raw_analysis.get("ctas", []),
            visual_themes=raw_analysis.get("visual_themes", []),
            target_audience=raw_analysis.get("target_audience", ""),
            emotional_appeal=raw_analysis.get("emotional_appeal", ""),
            marketing_effectiveness=MarketingEffectiveness(
                hook_strength=effectiveness.get("hook_strength", 5),
                message_clarity=effectiveness.get("message_clarity", 5),
                visual_impact=effectiveness.get("visual_impact", 5),
                cta_effectiveness=effectiveness.get("cta_effectiveness", 5),
                overall_score=effectiveness.get("overall_score", 5),
            ),
            strategic_insights=raw_analysis.get("strategic_insights", ""),
            reasoning=raw_analysis.get("reasoning", ""),
            video_analysis=video_analysis,
        )

    def extract_hook_score(self, raw_analysis: dict[str, Any]) -> int:
        """
        Extract hook score from the analysis.

        The hook score is derived from the first NarrativeBeat in the timeline
        or from the explicit hook_score field.

        Args:
            raw_analysis: Raw analysis dictionary from the AI

        Returns:
            Hook score (1-10)
        """
        # Check for explicit hook_score first
        if "hook_score" in raw_analysis:
            return max(1, min(10, raw_analysis["hook_score"]))

        # Fall back to overall_pacing_score
        if "overall_pacing_score" in raw_analysis:
            return max(1, min(10, raw_analysis["overall_pacing_score"]))

        return 5  # Default middle score

    # =========================================================================
    # V2 ENHANCED ANALYSIS METHODS
    # =========================================================================

    async def analyze_video_v2(
        self,
        video_content: bytes,
        competitor_name: str = "Unknown",
        market_position: str | None = None,
        follower_count: int | None = None,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        mime_type: str = "video/mp4",
        brand_name: str | None = None,
        industry: str | None = None,
        target_audience: str | None = None,
        platform_cta: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a video using the enhanced V2 prompt with full Creative DNA.

        Args:
            video_content: Video file content as bytes
            competitor_name: Name of the competitor
            market_position: Market position (leader, challenger, niche)
            follower_count: Number of followers
            likes: Number of likes on the ad
            comments: Number of comments
            shares: Number of shares
            mime_type: MIME type of the video
            brand_name: Brand name for context (optional)
            industry: Industry for context (optional)
            target_audience: Target audience context (optional)
            platform_cta: Platform CTA button text (optional, e.g. "Learn More")

        Returns:
            Enhanced analysis result dictionary (V2 schema)
        """
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_content)
            tmp_path = tmp.name

        try:
            video_file = self.client.files.upload(file=tmp_path, config={"mime_type": mime_type})

            while video_file.state == types.FileState.PROCESSING:
                time.sleep(2)
                video_file = self.client.files.get(name=video_file.name)

            if video_file.state == types.FileState.FAILED:
                raise VideoAnalysisError("Video processing failed in Gemini")

            prompt = VIDEO_ANALYSIS_PROMPT_V2.format(
                competitor_name=competitor_name,
                market_position=market_position or "Unknown",
                follower_count=follower_count or "Unknown",
                likes=likes,
                comments=comments,
                shares=shares,
                brand_name=brand_name or "Not provided",
                industry=industry or "Not provided",
                target_audience=target_audience or "Not provided",
                platform_cta=platform_cta or "Not specified",
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[video_file, prompt],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                    max_output_tokens=16384,
                ),
            )

            result_text = response.text
            if not result_text:
                raise VideoAnalysisError("Empty response from Gemini")

            result = json.loads(result_text.strip())

            # Handle multi-encoded JSON (Gemini sometimes returns a JSON string
            # containing a JSON string instead of a JSON object)
            max_decode_depth = 5
            decode_attempts = 0
            while isinstance(result, str) and decode_attempts < max_decode_depth:
                result = json.loads(result)
                decode_attempts += 1

            if not isinstance(result, dict):
                raise VideoAnalysisError(
                    f"Gemini response is not a JSON object after decoding. "
                    f"Got type: {type(result).__name__}"
                )

            self.client.files.delete(name=video_file.name)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini V2 response: {e}")
            raise VideoAnalysisError(f"Failed to parse analysis response: {e}") from e
        except Exception as e:
            logger.error(f"Video analysis V2 failed: {e}")
            raise VideoAnalysisError(f"Analysis failed: {e}") from e
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def analyze_from_storage_v2(
        self,
        storage_path: str,
        competitor_name: str = "Unknown",
        market_position: str | None = None,
        follower_count: int | None = None,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        brand_name: str | None = None,
        industry: str | None = None,
        target_audience: str | None = None,
        platform_cta: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a video from Supabase Storage using V2 enhanced analysis.

        Args:
            storage_path: Path to the video in storage
            competitor_name: Name of the competitor
            market_position: Market position
            follower_count: Number of followers
            likes: Number of likes
            comments: Number of comments
            shares: Number of shares
            brand_name: Brand name for context (optional)
            industry: Industry for context (optional)
            target_audience: Target audience context (optional)
            platform_cta: Platform CTA button text (optional)

        Returns:
            Enhanced analysis result dictionary (V2 schema)
        """
        video_content = await self.storage.download_file(storage_path)

        extension = storage_path.split(".")[-1].lower()
        mime_types = {
            "mp4": "video/mp4",
            "webm": "video/webm",
            "mov": "video/quicktime",
        }
        mime_type = mime_types.get(extension, "video/mp4")

        return await self.analyze_video_v2(
            video_content,
            competitor_name,
            market_position,
            follower_count,
            likes,
            comments,
            shares,
            mime_type,
            brand_name,
            industry,
            target_audience,
            platform_cta,
        )

    def _validate_ad_components(self, timeline: list[EnhancedNarrativeBeat]) -> None:
        """
        Validate that essential ad components are present in the timeline.

        Logs warnings if Hook or CTA are missing, as 99% of ads should have them.

        Args:
            timeline: List of parsed narrative beats
        """
        beat_types = {beat.beat_type for beat in timeline}

        if "Hook" not in beat_types:
            logger.warning(
                "No 'Hook' component found in timeline. "
                "Most ads should have a hook in the first 1-5 seconds."
            )

        if "CTA" not in beat_types:
            logger.warning(
                "No 'CTA' component found in timeline. Most ads should have a clear call-to-action."
            )

        # Log which key components were found for debugging
        key_components = ["Hook", "Problem", "Solution", "Product Showcase", "CTA"]
        found_components = [c for c in key_components if c in beat_types]
        logger.info(f"Ad components found: {found_components}")

    def parse_enhanced_analysis_v2(
        self, raw_analysis: dict[str, Any] | str
    ) -> EnhancedAdAnalysisV2:
        """
        Parse raw V2 analysis into an EnhancedAdAnalysisV2 schema.

        This method provides robust parsing with defaults for all fields,
        ensuring the analysis is always valid even if some fields are missing.

        Args:
            raw_analysis: Raw analysis dictionary from the AI (V2 format),
                or a JSON string that will be parsed first.

        Returns:
            EnhancedAdAnalysisV2 object with validated structure
        """
        try:
            print(raw_analysis)

            # Handle case where raw_analysis is a string (multi-encoded JSON).
            # Gemini can return triple+ encoded JSON, so loop until we get a dict.
            max_decode_depth = 5
            decode_attempts = 0
            while isinstance(raw_analysis, str) and decode_attempts < max_decode_depth:
                raw_analysis = json.loads(raw_analysis)
                decode_attempts += 1

            if not isinstance(raw_analysis, dict):
                raise VideoAnalysisError(
                    f"Analysis result is not a JSON object after {decode_attempts} decode attempts. "
                    f"Got type: {type(raw_analysis).__name__}"
                )

            # Parse timeline beats
            timeline = []
            print("[DEBUG] About to .get('timeline')")
            for beat_data in raw_analysis.get("timeline", []):
                beat = self._parse_enhanced_beat(beat_data)
                timeline.append(beat)

            # Validate that essential components are present
            self._validate_ad_components(timeline)

            # Parse copy analysis
            print("[DEBUG] About to .get('copy_analysis')")
            copy_data = raw_analysis.get("copy_analysis", {})
            copy_analysis = self._parse_copy_analysis(copy_data)

            # Parse audio analysis (video only)
            print("[DEBUG] About to .get('audio_analysis')")
            audio_data = raw_analysis.get("audio_analysis")
            audio_analysis = self._parse_audio_analysis(audio_data) if audio_data else None

            # Parse brand elements
            print("[DEBUG] About to .get('brand_elements')")
            brand_data = raw_analysis.get("brand_elements", {})
            brand_elements = self._parse_brand_elements(brand_data)

            # Parse engagement predictors
            print("[DEBUG] About to .get('engagement_predictors')")
            engagement_data = raw_analysis.get("engagement_predictors", {})
            engagement_predictors = self._parse_engagement_predictors(engagement_data)

            # Parse platform optimization
            print("[DEBUG] About to .get('platform_optimization')")
            platform_data = raw_analysis.get("platform_optimization", {})
            platform_optimization = self._parse_platform_optimization(platform_data)

            # Parse emotional arc (video only)
            print("[DEBUG] About to .get('emotional_arc')")
            emotional_data = raw_analysis.get("emotional_arc")
            emotional_arc = self._parse_emotional_arc(emotional_data) if emotional_data else None

            # Parse critique
            print("[DEBUG] About to .get('critique')")
            critique_data = raw_analysis.get("critique", {})
            critique = self._parse_critique(critique_data)

            print("[DEBUG] About to .get('media_type')")
            print("[DEBUG] About to .get('analysis_version')")
            print("[DEBUG] About to .get('analysis_confidence')")
            print("[DEBUG] About to .get('analysis_notes')")
            print("[DEBUG] About to .get('inferred_audience')")
            print("[DEBUG] About to .get('primary_messaging_pillar')")
            print("[DEBUG] About to .get('overall_pacing_score')")
            print("[DEBUG] About to .get('production_style')")
            print("[DEBUG] About to .get('hook_score')")
            print("[DEBUG] About to .get('overall_narrative_summary')")
            return EnhancedAdAnalysisV2(
                media_type=raw_analysis.get("media_type", "video"),
                analysis_version=raw_analysis.get("analysis_version", "2.0"),
                analysis_confidence=raw_analysis.get("analysis_confidence", 0.8),
                analysis_notes=raw_analysis.get("analysis_notes", []),
                inferred_audience=raw_analysis.get("inferred_audience", ""),
                primary_messaging_pillar=raw_analysis.get("primary_messaging_pillar", ""),
                overall_pacing_score=self._clamp_score(raw_analysis.get("overall_pacing_score", 5)),
                production_style=self._sanitize_literal(
                    raw_analysis.get("production_style"), self._VALID_PRODUCTION_STYLES
                ),
                hook_score=self._clamp_score(raw_analysis.get("hook_score", 5)),
                timeline=timeline,
                overall_narrative_summary=raw_analysis.get("overall_narrative_summary", ""),
                copy_analysis=copy_analysis,
                audio_analysis=audio_analysis,
                brand_elements=brand_elements,
                engagement_predictors=engagement_predictors,
                platform_optimization=platform_optimization,
                emotional_arc=emotional_arc,
                critique=critique,
            )

        except Exception as e:
            logger.error(f"Failed to parse enhanced analysis V2: {e}")
            raise VideoAnalysisError(f"Failed to parse enhanced analysis V2: {e}") from e

    def _clamp_score(self, value: Any, min_val: int = 1, max_val: int = 10) -> int:
        """Clamp a score value to valid range."""
        try:
            return max(min_val, min(max_val, int(value)))
        except (ValueError, TypeError):
            return 5

    def _sanitize_nullable(self, value: Any) -> Any:
        """Convert string 'null' to actual None for nullable fields."""
        if value is None or value == "null" or value == "None" or value == "":
            return None
        return value

    _VALID_COPY_FRAMEWORKS = {
        "PAS",
        "AIDA",
        "BAB",
        "FAB",
        "4Ps",
        "QUEST",
        "PASTOR",
        "SLAP",
        "STAR",
        "Custom",
        "Unknown",
    }
    _VALID_PRODUCTION_STYLES = {
        "High-production Studio",
        "Authentic UGC",
        "Hybrid",
        "Animation",
        "Stock Footage Mashup",
        "Screen Recording",
        "Talking Head",
        "Documentary Style",
        "Influencer Native",
        "Unknown",
    }

    def _sanitize_literal(self, value: Any, valid_set: set[str], fallback: str = "Unknown") -> str:
        """Validate a value against allowed literals, returning fallback if not matched."""
        value = self._sanitize_nullable(value)
        if value is None:
            return fallback
        if value in valid_set:
            return value
        return fallback

    def _normalize_beat_type(self, beat_type: str) -> str:
        """
        Normalize beat_type to valid AdComponentType values.

        Maps legacy or variant labels to the standard component types.

        Args:
            beat_type: Raw beat type from AI response

        Returns:
            Normalized beat type matching BeatType Literal
        """
        # Valid component types
        valid_types = {
            "Hook",
            "Problem",
            "Solution",
            "Product Showcase",
            "Social Proof",
            "Benefit Stack",
            "Objection Handling",
            "CTA",
            "Transition",
            "Unknown",
        }

        # Direct match
        if beat_type in valid_types:
            return beat_type

        # Mapping for legacy/variant labels to new standard types
        legacy_mapping = {
            # Old types -> New standard types
            "Feature Demo": "Product Showcase",
            "Testimonial": "Social Proof",
            "Objection Handler": "Objection Handling",
            "Comparison": "Product Showcase",
            "Story Setup": "Hook",
            "Emotional Peak": "Solution",
            "Brand Moment": "Transition",
            # Common variations
            "Call to Action": "CTA",
            "Call-to-Action": "CTA",
            "Product Demo": "Product Showcase",
            "Demo": "Product Showcase",
            "Showcase": "Product Showcase",
            "Benefits": "Benefit Stack",
            "Proof": "Social Proof",
            "Review": "Social Proof",
            "Testimonials": "Social Proof",
            "Introduction": "Hook",
            "Intro": "Hook",
            "Opener": "Hook",
            "Pain Point": "Problem",
            "Agitation": "Problem",
            "Reveal": "Solution",
            "Product Reveal": "Solution",
            "Objection": "Objection Handling",
            "Trust": "Objection Handling",
            "Guarantee": "Objection Handling",
        }

        # Check for mapping (case-insensitive)
        for key, value in legacy_mapping.items():
            if beat_type.lower() == key.lower():
                logger.debug(f"Mapped legacy beat_type '{beat_type}' to '{value}'")
                return value

        # If no match found, log warning and return Unknown
        logger.warning(f"Unknown beat_type '{beat_type}', defaulting to 'Unknown'")
        return "Unknown"

    def _parse_enhanced_beat(self, beat_data: dict[str, Any]) -> EnhancedNarrativeBeat:
        """Parse a single enhanced narrative beat."""
        cinematics_data = beat_data.get("cinematics", {})
        rhetorical_data = beat_data.get("rhetorical_appeal", {})

        cinematics = EnhancedCinematicDetails(
            camera_angle=cinematics_data.get("camera_angle", "Unknown"),
            lighting_style=cinematics_data.get("lighting_style", "Unknown"),
            cinematic_features=cinematics_data.get("cinematic_features", []),
            color_grading=cinematics_data.get("color_grading"),
            motion_type=cinematics_data.get("motion_type"),
            transition_in=cinematics_data.get("transition_in"),
            transition_out=cinematics_data.get("transition_out"),
        )

        rhetorical_appeal = EnhancedRhetoricalAppeal(
            mode=rhetorical_data.get("mode", "Unknown"),
            description=rhetorical_data.get("description", ""),
            secondary_mode=self._sanitize_nullable(rhetorical_data.get("secondary_mode")),
            persuasion_techniques=rhetorical_data.get("persuasion_techniques", []),
            objection_addressed=self._sanitize_nullable(rhetorical_data.get("objection_addressed")),
        )

        text_overlays = [
            TextOverlay(
                text=t.get("text", ""),
                timestamp=t.get("timestamp", "00:00"),
                duration_seconds=t.get("duration_seconds", 0),
                position=t.get("position", "center"),
                typography=t.get("typography"),
                animation=t.get("animation"),
                emphasis_type=t.get("emphasis_type"),
                purpose=t.get("purpose"),
            )
            for t in beat_data.get("text_overlays_in_beat", [])
        ]

        # Normalize beat_type to valid AdComponentType
        raw_beat_type = beat_data.get("beat_type", "Unknown")
        normalized_beat_type = self._normalize_beat_type(raw_beat_type)

        return EnhancedNarrativeBeat(
            start_time=beat_data.get("start_time", "00:00"),
            end_time=beat_data.get("end_time", "00:00"),
            beat_type=normalized_beat_type,
            cinematics=cinematics,
            tone_of_voice=beat_data.get("tone_of_voice", ""),
            rhetorical_appeal=rhetorical_appeal,
            target_audience_cues=beat_data.get("target_audience_cues", ""),
            visual_description=beat_data.get("visual_description", ""),
            audio_transcript=beat_data.get("audio_transcript", ""),
            emotion=self._sanitize_nullable(beat_data.get("emotion")),
            emotion_intensity=self._clamp_score(beat_data["emotion_intensity"])
            if beat_data.get("emotion_intensity")
            else None,
            text_overlays_in_beat=text_overlays,
            key_visual_elements=beat_data.get("key_visual_elements", []),
            attention_score=self._clamp_score(beat_data["attention_score"])
            if beat_data.get("attention_score")
            else None,
            improvement_note=self._sanitize_nullable(beat_data.get("improvement_note")),
        )

    def _parse_copy_analysis(self, data: dict[str, Any]) -> CopyAnalysis:
        """Parse copy analysis section."""
        raw_overlays = data.get("all_text_overlays", [])
        text_overlays = []
        for t in raw_overlays:
            if isinstance(t, str):
                text_overlays.append(TextOverlay(text=t))
            elif isinstance(t, dict):
                text_overlays.append(
                    TextOverlay(
                        text=t.get("text", ""),
                        timestamp=t.get("timestamp", "00:00"),
                        duration_seconds=t.get("duration_seconds", 0),
                        position=t.get("position", "center"),
                        typography=t.get("typography"),
                        animation=t.get("animation"),
                        emphasis_type=t.get("emphasis_type"),
                        purpose=t.get("purpose"),
                    )
                )

        return CopyAnalysis(
            all_text_overlays=text_overlays,
            headline_text=self._sanitize_nullable(data.get("headline_text")),
            body_copy=self._sanitize_nullable(data.get("body_copy")),
            cta_text=self._sanitize_nullable(data.get("cta_text")),
            copy_framework=self._sanitize_literal(
                data.get("copy_framework"), self._VALID_COPY_FRAMEWORKS
            ),
            framework_execution=self._sanitize_nullable(data.get("framework_execution")),
            reading_level=self._sanitize_nullable(data.get("reading_level")),
            word_count=data.get("word_count"),
            power_words=data.get("power_words", []),
            sensory_words=data.get("sensory_words", []),
        )

    def _parse_audio_analysis(self, data: dict[str, Any]) -> AudioAnalysis:
        """Parse audio analysis section."""
        music_data = data.get("music", {})
        voice_data = data.get("voice", {})

        music = MusicAnalysis(
            has_music=music_data.get("has_music", False),
            genre=music_data.get("genre"),
            tempo=music_data.get("tempo"),
            energy_level=music_data.get("energy_level"),
            mood=music_data.get("mood"),
            music_sync_moments=music_data.get("music_sync_moments", []),
            drop_timestamps=music_data.get("drop_timestamps", []),
        )

        voice = VoiceAnalysis(
            has_voiceover=voice_data.get("has_voiceover", False),
            has_dialogue=voice_data.get("has_dialogue", False),
            voice_gender=voice_data.get("voice_gender"),
            voice_age_range=voice_data.get("voice_age_range"),
            voice_tone=voice_data.get("voice_tone"),
            estimated_wpm=voice_data.get("estimated_wpm"),
            accent=voice_data.get("accent"),
        )

        from app.schemas.ad_analysis import SoundEffectMarker

        sound_effects = [
            SoundEffectMarker(
                timestamp=s.get("timestamp", "00:00"),
                sfx_type=s.get("sfx_type", "unknown"),
                purpose=s.get("purpose"),
            )
            for s in data.get("sound_effects", [])
        ]

        return AudioAnalysis(
            music=music,
            voice=voice,
            sound_effects=sound_effects,
            audio_visual_sync_score=self._clamp_score(data["audio_visual_sync_score"])
            if data.get("audio_visual_sync_score")
            else None,
            silence_moments=data.get("silence_moments", []),
            sound_off_compatible=data.get("sound_off_compatible", False),
        )

    def _parse_brand_elements(self, data: dict[str, Any]) -> BrandElements:
        """Parse brand elements section."""
        from app.schemas.ad_analysis import LogoAppearance, ProductAppearance

        logo_appearances = [
            LogoAppearance(
                timestamp=logo.get("timestamp", "00:00"),
                duration_seconds=logo.get("duration_seconds", 0),
                position=logo.get("position", "corner"),
                size=logo.get("size", "small"),
                animation=logo.get("animation"),
            )
            for logo in data.get("logo_appearances", [])
        ]

        product_appearances = [
            ProductAppearance(
                timestamp=p.get("timestamp", "00:00"),
                duration_seconds=p.get("duration_seconds", 0),
                shot_type=p.get("shot_type", "hero shot"),
                prominence=p.get("prominence", "primary focus"),
                context=p.get("context"),
            )
            for p in data.get("product_appearances", [])
        ]

        return BrandElements(
            logo_appearances=logo_appearances,
            logo_visible=data.get("logo_visible", False),
            logo_position=data.get("logo_position"),
            brand_colors_detected=data.get("brand_colors_detected", []),
            brand_color_consistency=self._clamp_score(data["brand_color_consistency"])
            if data.get("brand_color_consistency")
            else None,
            product_appearances=product_appearances,
            has_product_shot=data.get("has_product_shot", False),
            product_visibility_seconds=data.get("product_visibility_seconds"),
            brand_mentions_audio=data.get("brand_mentions_audio", 0),
            brand_mentions_text=data.get("brand_mentions_text", 0),
        )

    def _parse_engagement_predictors(self, data: dict[str, Any]) -> EngagementPredictors:
        """Parse engagement predictors section."""
        thumb_data = data.get("thumb_stop", {})

        thumb_stop = ThumbStopAnalysis(
            thumb_stop_score=self._clamp_score(thumb_data.get("thumb_stop_score", 5)),
            first_frame_hook=thumb_data.get("first_frame_hook", ""),
            pattern_interrupt_type=thumb_data.get("pattern_interrupt_type"),
            curiosity_gap=thumb_data.get("curiosity_gap", False),
            curiosity_gap_description=thumb_data.get("curiosity_gap_description"),
            first_second_elements=thumb_data.get("first_second_elements", []),
            visual_contrast_score=self._clamp_score(thumb_data["visual_contrast_score"])
            if thumb_data.get("visual_contrast_score")
            else None,
            text_hook_present=thumb_data.get("text_hook_present", False),
            face_in_first_frame=thumb_data.get("face_in_first_frame", False),
        )

        return EngagementPredictors(
            thumb_stop=thumb_stop,
            scene_change_frequency=data.get("scene_change_frequency"),
            visual_variety_score=self._clamp_score(data.get("visual_variety_score", 5)),
            uses_fear_of_missing_out=data.get("uses_fear_of_missing_out", False),
            uses_social_proof_signals=data.get("uses_social_proof_signals", False),
            uses_controversy_or_hot_take=data.get("uses_controversy_or_hot_take", False),
            uses_transformation_narrative=data.get("uses_transformation_narrative", False),
            predicted_watch_through_rate=data.get("predicted_watch_through_rate"),
            predicted_engagement_type=data.get("predicted_engagement_type"),
        )

    def _parse_platform_optimization(self, data: dict[str, Any]) -> PlatformOptimization:
        """Parse platform optimization section."""
        return PlatformOptimization(
            aspect_ratio=data.get("aspect_ratio", "Unknown"),
            optimal_platforms=data.get("optimal_platforms", []),
            sound_off_compatible=data.get("sound_off_compatible", False),
            caption_dependency=data.get("caption_dependency", "medium"),
            native_feel_score=self._clamp_score(data.get("native_feel_score", 5)),
            native_elements=data.get("native_elements", []),
            duration_seconds=data.get("duration_seconds"),
            ideal_duration_assessment=data.get("ideal_duration_assessment"),
            safe_zone_compliance=data.get("safe_zone_compliance", True),
        )

    def _parse_emotional_arc(self, data: dict[str, Any]) -> EmotionalArc:
        """Parse emotional arc section."""
        from app.schemas.ad_analysis import EmotionalBeatMarker

        emotional_beats = [
            EmotionalBeatMarker(
                timestamp=e.get("timestamp", "00:00"),
                primary_emotion=e.get("primary_emotion", "neutral"),
                intensity=self._clamp_score(e.get("intensity", 5)),
                trigger=e.get("trigger", ""),
            )
            for e in data.get("emotional_beats", [])
        ]

        return EmotionalArc(
            emotional_beats=emotional_beats,
            emotional_climax_timestamp=self._sanitize_nullable(
                data.get("emotional_climax_timestamp")
            ),
            tension_build_pattern=self._sanitize_nullable(data.get("tension_build_pattern")),
            resolution_type=self._sanitize_nullable(data.get("resolution_type")),
            dominant_emotional_tone=data.get("dominant_emotional_tone", "neutral"),
        )

    def _parse_critique(self, data: dict[str, Any]) -> AdCritique:
        """Parse critique section."""
        from app.schemas.ad_analysis import RemakeSuggestion, StrengthItem, WeaknessItem

        strengths = [
            StrengthItem(
                strength=s.get("strength", ""),
                evidence=s.get("evidence", ""),
                timestamp=s.get("timestamp"),
                impact=s.get("impact", ""),
            )
            for s in data.get("strengths", [])
        ]

        weaknesses = [
            WeaknessItem(
                weakness=w.get("weakness", ""),
                evidence=w.get("evidence", ""),
                timestamp=w.get("timestamp"),
                impact=w.get("impact", ""),
                suggested_fix=w.get("suggested_fix", ""),
            )
            for w in data.get("weaknesses", [])
        ]

        remake_suggestions = [
            RemakeSuggestion(
                section_to_remake=r.get("section_to_remake", ""),
                current_approach=r.get("current_approach", ""),
                suggested_approach=r.get("suggested_approach", ""),
                expected_improvement=r.get("expected_improvement", ""),
                effort_level=r.get("effort_level", "moderate edit"),
                priority=r.get("priority", "medium"),
            )
            for r in data.get("remake_suggestions", [])
        ]

        return AdCritique(
            overall_grade=data.get("overall_grade", "C"),
            overall_assessment=data.get("overall_assessment", ""),
            strengths=strengths,
            weaknesses=weaknesses,
            remake_suggestions=remake_suggestions,
            quick_wins=data.get("quick_wins", []),
            competitive_position=data.get("competitive_position"),
        )

    def get_video_intelligence(
        self, analysis: dict[str, Any] | EnhancedAdAnalysisV2
    ) -> dict[str, Any]:
        """
        Extract V2 video intelligence data for persistence in JSONB column.

        This returns the validated and structured Creative DNA V2 that can be
        stored directly in the video_intelligence column.

        Args:
            analysis: Either raw analysis dict or already-parsed EnhancedAdAnalysisV2

        Returns:
            Validated video intelligence dictionary ready for JSONB storage
        """
        if isinstance(analysis, EnhancedAdAnalysisV2):
            return analysis.model_dump()
        enhanced = self.parse_enhanced_analysis_v2(analysis)
        return enhanced.model_dump()
