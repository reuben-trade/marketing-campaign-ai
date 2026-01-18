"""Image analysis service using GPT-4 Vision."""

import base64
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.ad import AdAnalysis, MarketingEffectiveness
from app.utils.prompts import IMAGE_ANALYSIS_PROMPT
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
