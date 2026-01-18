"""Video analysis service using Google Gemini."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

import google.generativeai as genai

from app.config import get_settings
from app.schemas.ad import AdAnalysis, MarketingEffectiveness, VideoAnalysis
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
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-pro")
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
            video_file = genai.upload_file(tmp_path, mime_type=mime_type)

            while video_file.state.name == "PROCESSING":
                import time
                time.sleep(2)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise VideoAnalysisError("Video processing failed in Gemini")

            prompt = VIDEO_ANALYSIS_PROMPT.format(
                competitor_name=competitor_name,
                market_position=market_position or "Unknown",
                follower_count=follower_count or "Unknown",
                likes=likes,
                comments=comments,
                shares=shares,
            )

            response = self.model.generate_content(
                [video_file, prompt],
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 4000,
                },
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

            genai.delete_file(video_file.name)

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
