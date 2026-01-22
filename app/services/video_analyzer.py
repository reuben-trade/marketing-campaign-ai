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
    CinematicDetails,
    EnhancedAdAnalysis,
    NarrativeBeat,
    RhetoricalAppeal,
)
from app.utils.prompts import VIDEO_ANALYSIS_PROMPT
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

    async def analyze_video(
        self,
        video_content: bytes,
        competitor_name: str,
        market_position: str | None = None,
        follower_count: int | None = None,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        mime_type: str = "video/mp4",
    ) -> dict[str, Any]:
        """
        Analyze an ad video using Google Gemini.

        Args:
            video_content: Video file content as bytes
            competitor_name: Name of the competitor
            market_position: Market position (leader, challenger, niche)
            follower_count: Number of followers
            likes: Number of likes on the ad
            comments: Number of comments
            shares: Number of shares
            mime_type: MIME type of the video

        Returns:
            Analysis result dictionary
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

            prompt = VIDEO_ANALYSIS_PROMPT.format(
                competitor_name=competitor_name,
                market_position=market_position or "Unknown",
                follower_count=follower_count or "Unknown",
                likes=likes,
                comments=comments,
                shares=shares,
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[video_file, prompt],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=4000,
                ),
            )

            result_text = response.text
            if not result_text:
                raise VideoAnalysisError("Empty response from Gemini")

            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())

            self.client.files.delete(name=video_file.name)

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise VideoAnalysisError(f"Failed to parse analysis response: {e}") from e
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            raise VideoAnalysisError(f"Analysis failed: {e}") from e
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def analyze_from_storage(
        self,
        storage_path: str,
        competitor_name: str,
        market_position: str | None = None,
        follower_count: int | None = None,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
    ) -> dict[str, Any]:
        """
        Analyze a video from Supabase Storage.

        Args:
            storage_path: Path to the video in storage
            competitor_name: Name of the competitor
            market_position: Market position
            follower_count: Number of followers
            likes: Number of likes
            comments: Number of comments
            shares: Number of shares

        Returns:
            Analysis result dictionary
        """
        video_content = await self.storage.download_file(storage_path)

        extension = storage_path.split(".")[-1].lower()
        mime_types = {
            "mp4": "video/mp4",
            "webm": "video/webm",
            "mov": "video/quicktime",
        }
        mime_type = mime_types.get(extension, "video/mp4")

        return await self.analyze_video(
            video_content,
            competitor_name,
            market_position,
            follower_count,
            likes,
            comments,
            shares,
            mime_type,
        )

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

    def parse_enhanced_analysis(self, raw_analysis: dict[str, Any]) -> EnhancedAdAnalysis:
        """
        Parse raw analysis into an EnhancedAdAnalysis schema with narrative beats.

        Args:
            raw_analysis: Raw analysis dictionary from the AI (new format)

        Returns:
            EnhancedAdAnalysis object with validated structure

        Raises:
            VideoAnalysisError: If the response doesn't match expected schema
        """
        try:
            # Parse timeline beats
            timeline = []
            for beat_data in raw_analysis.get("timeline", []):
                cinematics_data = beat_data.get("cinematics", {})
                rhetorical_data = beat_data.get("rhetorical_appeal", {})

                cinematics = CinematicDetails(
                    camera_angle=cinematics_data.get("camera_angle", "Unknown"),
                    lighting_style=cinematics_data.get("lighting_style", "Unknown"),
                    cinematic_features=cinematics_data.get("cinematic_features", []),
                )

                rhetorical_appeal = RhetoricalAppeal(
                    mode=rhetorical_data.get("mode", "Unknown"),
                    description=rhetorical_data.get("description", ""),
                )

                beat = NarrativeBeat(
                    start_time=beat_data.get("start_time", "00:00"),
                    end_time=beat_data.get("end_time", "00:00"),
                    beat_type=beat_data.get("beat_type", "Unknown"),
                    cinematics=cinematics,
                    tone_of_voice=beat_data.get("tone_of_voice", ""),
                    rhetorical_appeal=rhetorical_appeal,
                    target_audience_cues=beat_data.get("target_audience_cues", ""),
                    visual_description=beat_data.get("visual_description", ""),
                    audio_transcript=beat_data.get("audio_transcript", ""),
                )
                timeline.append(beat)

            # Derive hook_score from first beat if not provided
            hook_score = raw_analysis.get("hook_score")
            if hook_score is None and timeline:
                # Default to overall_pacing_score if hook_score not explicitly set
                hook_score = raw_analysis.get("overall_pacing_score", 5)

            return EnhancedAdAnalysis(
                inferred_audience=raw_analysis.get("inferred_audience", ""),
                primary_messaging_pillar=raw_analysis.get("primary_messaging_pillar", ""),
                overall_pacing_score=raw_analysis.get("overall_pacing_score", 5),
                production_style=raw_analysis.get("production_style", "Unknown"),
                hook_score=hook_score if hook_score is not None else 5,
                timeline=timeline,
                overall_narrative_summary=raw_analysis.get("overall_narrative_summary", ""),
            )

        except Exception as e:
            logger.error(f"Failed to parse enhanced analysis: {e}")
            raise VideoAnalysisError(f"Failed to parse enhanced analysis: {e}") from e

    def get_video_intelligence(self, raw_analysis: dict[str, Any]) -> dict[str, Any]:
        """
        Extract video intelligence data for persistence in JSONB column.

        This returns the validated and structured Creative DNA that can be
        stored directly in the video_intelligence column for future AI critiques.

        Args:
            raw_analysis: Raw analysis dictionary from the AI

        Returns:
            Validated video intelligence dictionary ready for JSONB storage
        """
        enhanced = self.parse_enhanced_analysis(raw_analysis)
        return enhanced.model_dump()

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
