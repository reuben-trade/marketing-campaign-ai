"""Image analysis service using GPT-4 Vision."""

import base64
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.ad import AdAnalysis, MarketingEffectiveness
from app.schemas.ad_analysis import (
    AdCritique,
    BrandElements,
    CopyAnalysis,
    EngagementPredictors,
    EnhancedAdAnalysisV2,
    PlatformOptimization,
    RemakeSuggestion,
    StrengthItem,
    TextOverlay,
    ThumbStopAnalysis,
    WeaknessItem,
)
from app.utils.prompts import IMAGE_ANALYSIS_PROMPT, IMAGE_ANALYSIS_PROMPT_V2
from app.utils.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)


class ImageAnalysisError(Exception):
    """Exception raised when image analysis fails."""

    pass


class ImageAnalyzer:
    """Analyzes ad images using GPT-4 Vision."""

    def __init__(self) -> None:
        """Initialize the image analyzer."""
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.storage = SupabaseStorage()

    async def analyze_image(
        self,
        image_content: bytes,
        competitor_name: str,
        market_position: str | None = None,
        follower_count: int | None = None,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
    ) -> dict[str, Any]:
        """
        Analyze an ad image using GPT-4 Vision.

        Args:
            image_content: Image file content as bytes
            competitor_name: Name of the competitor
            market_position: Market position (leader, challenger, niche)
            follower_count: Number of followers
            likes: Number of likes on the ad
            comments: Number of comments
            shares: Number of shares

        Returns:
            Analysis result dictionary
        """
        base64_image = base64.b64encode(image_content).decode("utf-8")

        prompt = IMAGE_ANALYSIS_PROMPT.format(
            competitor_name=competitor_name,
            market_position=market_position or "Unknown",
            follower_count=follower_count or "Unknown",
            likes=likes,
            comments=comments,
            shares=shares,
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=4000,
                temperature=0.3,
            )

            result_text = response.choices[0].message.content
            if not result_text:
                raise ImageAnalysisError("Empty response from GPT-4 Vision")

            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4 Vision response: {e}")
            raise ImageAnalysisError(f"Failed to parse analysis response: {e}") from e
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise ImageAnalysisError(f"Analysis failed: {e}") from e

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
        Analyze an image from Supabase Storage.

        Args:
            storage_path: Path to the image in storage
            competitor_name: Name of the competitor
            market_position: Market position
            follower_count: Number of followers
            likes: Number of likes
            comments: Number of comments
            shares: Number of shares

        Returns:
            Analysis result dictionary
        """
        image_content = await self.storage.download_file(storage_path)
        return await self.analyze_image(
            image_content,
            competitor_name,
            market_position,
            follower_count,
            likes,
            comments,
            shares,
        )

    async def analyze_from_url(
        self,
        image_url: str,
        competitor_name: str,
        market_position: str | None = None,
        follower_count: int | None = None,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
    ) -> dict[str, Any]:
        """
        Analyze an image directly from a URL.

        Args:
            image_url: Public URL of the image
            competitor_name: Name of the competitor
            market_position: Market position
            follower_count: Number of followers
            likes: Number of likes
            comments: Number of comments
            shares: Number of shares

        Returns:
            Analysis result dictionary
        """
        prompt = IMAGE_ANALYSIS_PROMPT.format(
            competitor_name=competitor_name,
            market_position=market_position or "Unknown",
            follower_count=follower_count or "Unknown",
            likes=likes,
            comments=comments,
            shares=shares,
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url, "detail": "high"},
                            },
                        ],
                    }
                ],
                max_tokens=4000,
                temperature=0.3,
            )

            result_text = response.choices[0].message.content
            if not result_text:
                raise ImageAnalysisError("Empty response from GPT-4 Vision")

            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            return json.loads(result_text.strip())

        except json.JSONDecodeError as e:
            raise ImageAnalysisError(f"Failed to parse analysis response: {e}") from e
        except Exception as e:
            raise ImageAnalysisError(f"Analysis failed: {e}") from e

    def parse_analysis(self, raw_analysis: dict[str, Any]) -> AdAnalysis:
        """
        Parse raw analysis into an AdAnalysis schema.

        Args:
            raw_analysis: Raw analysis dictionary from the AI

        Returns:
            AdAnalysis object
        """
        effectiveness = raw_analysis.get("marketing_effectiveness", {})

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
        )

    # =========================================================================
    # V2 ENHANCED ANALYSIS METHODS
    # =========================================================================

    async def analyze_image_v2(
        self,
        image_content: bytes,
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
        Analyze an image using the enhanced V2 prompt with full Creative DNA.

        Args:
            image_content: Image file content as bytes
            competitor_name: Name of the competitor
            market_position: Market position (leader, challenger, niche)
            follower_count: Number of followers
            likes: Number of likes on the ad
            comments: Number of comments
            shares: Number of shares
            brand_name: Brand name for context (optional)
            industry: Industry for context (optional)
            target_audience: Target audience context (optional)
            platform_cta: Platform CTA button text (optional, e.g. "Learn More")

        Returns:
            Enhanced analysis result dictionary (V2 schema)
        """
        base64_image = base64.b64encode(image_content).decode("utf-8")

        prompt = IMAGE_ANALYSIS_PROMPT_V2.format(
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

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=8000,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content
            if not result_text:
                raise ImageAnalysisError("Empty response from GPT-4 Vision")

            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4 Vision V2 response: {e}")
            raise ImageAnalysisError(f"Failed to parse analysis response: {e}") from e
        except Exception as e:
            logger.error(f"Image analysis V2 failed: {e}")
            raise ImageAnalysisError(f"Analysis failed: {e}") from e

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
        Analyze an image from Supabase Storage using V2 enhanced analysis.

        Args:
            storage_path: Path to the image in storage
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
        image_content = await self.storage.download_file(storage_path)
        return await self.analyze_image_v2(
            image_content,
            competitor_name,
            market_position,
            follower_count,
            likes,
            comments,
            shares,
            brand_name,
            industry,
            target_audience,
            platform_cta,
        )

    def parse_enhanced_analysis_v2(
        self, raw_analysis: dict[str, Any]
    ) -> EnhancedAdAnalysisV2:
        """
        Parse raw V2 image analysis into an EnhancedAdAnalysisV2 schema.

        This method provides robust parsing with defaults for all fields,
        ensuring the analysis is always valid even if some fields are missing.
        For images, video-only fields (timeline, audio_analysis, emotional_arc)
        are set to empty/None.

        Args:
            raw_analysis: Raw analysis dictionary from the AI (V2 format)

        Returns:
            EnhancedAdAnalysisV2 object with validated structure
        """
        try:
            # Parse copy analysis
            copy_data = raw_analysis.get("copy_analysis", {})
            copy_analysis = self._parse_copy_analysis(copy_data)

            # Parse brand elements
            brand_data = raw_analysis.get("brand_elements", {})
            brand_elements = self._parse_brand_elements(brand_data)

            # Parse engagement predictors
            engagement_data = raw_analysis.get("engagement_predictors", {})
            engagement_predictors = self._parse_engagement_predictors(engagement_data)

            # Parse platform optimization
            platform_data = raw_analysis.get("platform_optimization", {})
            platform_optimization = self._parse_platform_optimization(platform_data)

            # Parse critique
            critique_data = raw_analysis.get("critique", {})
            critique = self._parse_critique(critique_data)

            return EnhancedAdAnalysisV2(
                media_type="image",
                analysis_version=raw_analysis.get("analysis_version", "2.0"),
                analysis_confidence=raw_analysis.get("analysis_confidence", 0.8),
                analysis_notes=raw_analysis.get("analysis_notes", []),
                inferred_audience=raw_analysis.get("inferred_audience", ""),
                primary_messaging_pillar=raw_analysis.get("primary_messaging_pillar", ""),
                overall_pacing_score=self._clamp_score(
                    raw_analysis.get("overall_pacing_score", 5)
                ),
                production_style=raw_analysis.get("production_style", "Unknown"),
                hook_score=self._clamp_score(raw_analysis.get("hook_score", 5)),
                timeline=[],  # Images don't have timeline
                overall_narrative_summary=raw_analysis.get("overall_narrative_summary", ""),
                copy_analysis=copy_analysis,
                audio_analysis=None,  # Images don't have audio
                brand_elements=brand_elements,
                engagement_predictors=engagement_predictors,
                platform_optimization=platform_optimization,
                emotional_arc=None,  # Images don't have emotional arc
                critique=critique,
            )

        except Exception as e:
            logger.error(f"Failed to parse enhanced image analysis V2: {e}")
            raise ImageAnalysisError(f"Failed to parse enhanced analysis V2: {e}") from e

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

    def _parse_copy_analysis(self, data: dict[str, Any]) -> CopyAnalysis:
        """Parse copy analysis section."""
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
            for t in data.get("all_text_overlays", [])
        ]

        return CopyAnalysis(
            all_text_overlays=text_overlays,
            headline_text=self._sanitize_nullable(data.get("headline_text")),
            body_copy=self._sanitize_nullable(data.get("body_copy")),
            cta_text=self._sanitize_nullable(data.get("cta_text")),
            copy_framework=self._sanitize_nullable(data.get("copy_framework")),
            framework_execution=self._sanitize_nullable(data.get("framework_execution")),
            reading_level=self._sanitize_nullable(data.get("reading_level")),
            word_count=data.get("word_count"),
            power_words=data.get("power_words", []),
            sensory_words=data.get("sensory_words", []),
        )

    def _parse_brand_elements(self, data: dict[str, Any]) -> BrandElements:
        """Parse brand elements section (simplified for images)."""
        return BrandElements(
            logo_appearances=[],  # No timestamps for images
            logo_visible=data.get("logo_visible", False),
            logo_position=self._sanitize_nullable(data.get("logo_position")),
            brand_colors_detected=data.get("brand_colors_detected", []),
            brand_color_consistency=data.get("brand_color_consistency"),
            product_appearances=[],  # No timestamps for images
            has_product_shot=data.get("has_product_shot", False),
            product_visibility_seconds=None,
            brand_mentions_audio=0,
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
            visual_contrast_score=thumb_data.get("visual_contrast_score"),
            text_hook_present=thumb_data.get("text_hook_present", False),
            face_in_first_frame=thumb_data.get("face_in_first_frame", False),
        )

        return EngagementPredictors(
            thumb_stop=thumb_stop,
            scene_change_frequency=None,  # N/A for images
            visual_variety_score=self._clamp_score(data.get("visual_variety_score", 5)),
            uses_fear_of_missing_out=data.get("uses_fear_of_missing_out", False),
            uses_social_proof_signals=data.get("uses_social_proof_signals", False),
            uses_controversy_or_hot_take=data.get("uses_controversy_or_hot_take", False),
            uses_transformation_narrative=data.get("uses_transformation_narrative", False),
            predicted_watch_through_rate=None,  # N/A for images
            predicted_engagement_type=self._sanitize_nullable(data.get("predicted_engagement_type")),
        )

    def _parse_platform_optimization(self, data: dict[str, Any]) -> PlatformOptimization:
        """Parse platform optimization section."""
        return PlatformOptimization(
            aspect_ratio=data.get("aspect_ratio", "Unknown"),
            optimal_platforms=data.get("optimal_platforms", []),
            sound_off_compatible=True,  # Always true for images
            caption_dependency=data.get("caption_dependency", "none"),
            native_feel_score=self._clamp_score(data.get("native_feel_score", 5)),
            native_elements=data.get("native_elements", []),
            duration_seconds=None,  # N/A for images
            ideal_duration_assessment=None,  # N/A for images
            safe_zone_compliance=data.get("safe_zone_compliance", True),
        )

    def _parse_critique(self, data: dict[str, Any]) -> AdCritique:
        """Parse critique section."""
        strengths = [
            StrengthItem(
                strength=s.get("strength", ""),
                evidence=s.get("evidence", ""),
                timestamp=None,  # No timestamps for images
                impact=s.get("impact", ""),
            )
            for s in data.get("strengths", [])
        ]

        weaknesses = [
            WeaknessItem(
                weakness=w.get("weakness", ""),
                evidence=w.get("evidence", ""),
                timestamp=None,  # No timestamps for images
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
            competitive_position=self._sanitize_nullable(data.get("competitive_position")),
        )

    def get_image_intelligence_v2(
        self, analysis: dict[str, Any] | EnhancedAdAnalysisV2
    ) -> dict[str, Any]:
        """
        Extract V2 image intelligence data for persistence in JSONB column.

        This returns the validated and structured Creative DNA V2 that can be
        stored directly in the video_intelligence column (works for images too).

        Args:
            analysis: Either raw analysis dict or already-parsed EnhancedAdAnalysisV2

        Returns:
            Validated intelligence dictionary ready for JSONB storage
        """
        if isinstance(analysis, EnhancedAdAnalysisV2):
            return analysis.model_dump()
        enhanced = self.parse_enhanced_analysis_v2(analysis)
        return enhanced.model_dump()
