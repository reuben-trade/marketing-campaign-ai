"""Recommendation engine for generating content recommendations."""

import json
import logging
import time
from collections import Counter
from typing import Any
from uuid import UUID

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import get_settings
from app.utils.prompts import RECOMMENDATION_GENERATION_PROMPT

logger = logging.getLogger(__name__)


class RecommendationError(Exception):
    """Exception raised when recommendation generation fails."""

    pass


class RecommendationEngine:
    """Generates content recommendations based on competitor analysis."""

    def __init__(self) -> None:
        """Initialize the recommendation engine."""
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.default_model = settings.recommendation_model

    def _prepare_business_strategy_context(self, strategy: dict[str, Any]) -> str:
        """Prepare business strategy for the prompt."""
        return json.dumps(strategy, indent=2, default=str)

    def _prepare_ads_analysis_context(self, ads: list[dict[str, Any]]) -> str:
        """Prepare ads analysis for the prompt."""
        summarized_ads = []
        for ad in ads:
            analysis = ad.get("analysis", {})
            summarized_ads.append({
                "ad_id": str(ad.get("id", "")),
                "competitor": ad.get("competitor_name", "Unknown"),
                "creative_type": ad.get("creative_type", "unknown"),
                "engagement": {
                    "likes": ad.get("likes", 0),
                    "comments": ad.get("comments", 0),
                    "shares": ad.get("shares", 0),
                },
                "analysis": {
                    "summary": analysis.get("summary", ""),
                    "uvps": analysis.get("uvps", []),
                    "ctas": analysis.get("ctas", []),
                    "visual_themes": analysis.get("visual_themes", []),
                    "emotional_appeal": analysis.get("emotional_appeal", ""),
                    "marketing_effectiveness": analysis.get("marketing_effectiveness", {}),
                    "strategic_insights": analysis.get("strategic_insights", ""),
                },
            })
        return json.dumps(summarized_ads, indent=2, default=str)

    def _extract_trends(self, ads: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract trend data from analyzed ads."""
        visual_themes: list[str] = []
        ctas: list[str] = []
        emotional_appeals: list[str] = []
        total_engagement = 0

        for ad in ads:
            analysis = ad.get("analysis", {})
            visual_themes.extend(analysis.get("visual_themes", []))
            ctas.extend(analysis.get("ctas", []))
            if analysis.get("emotional_appeal"):
                emotional_appeals.append(analysis["emotional_appeal"])
            total_engagement += (
                ad.get("likes", 0) + ad.get("comments", 0) + ad.get("shares", 0)
            )

        avg_engagement = total_engagement / len(ads) if ads else 0

        theme_counts = Counter(visual_themes)
        cta_counts = Counter(ctas)

        return {
            "total_ads": len(ads),
            "avg_engagement": round(avg_engagement, 2),
            "visual_themes": ", ".join([t for t, _ in theme_counts.most_common(5)]),
            "messaging_patterns": ", ".join([e for e in Counter(emotional_appeals).most_common(3)]),
            "top_ctas": ", ".join([c for c, _ in cta_counts.most_common(5)]),
        }

    async def generate_recommendations(
        self,
        business_strategy: dict[str, Any],
        analyzed_ads: list[dict[str, Any]],
        model: str | None = None,
    ) -> tuple[dict[str, Any], float, str]:
        """
        Generate content recommendations based on strategy and ad analysis.

        Args:
            business_strategy: Business strategy dictionary
            analyzed_ads: List of analyzed ad dictionaries
            model: Model to use ("claude" or "openai"), defaults to config

        Returns:
            Tuple of (recommendations dict, generation time in seconds, model used)
        """
        model = model or self.default_model
        start_time = time.time()

        strategy_context = self._prepare_business_strategy_context(business_strategy)
        ads_context = self._prepare_ads_analysis_context(analyzed_ads)
        trends = self._extract_trends(analyzed_ads)

        prompt = RECOMMENDATION_GENERATION_PROMPT.format(
            business_strategy=strategy_context,
            ads_analysis=ads_context,
            total_ads=trends["total_ads"],
            avg_engagement=trends["avg_engagement"],
            visual_themes=trends["visual_themes"],
            messaging_patterns=trends["messaging_patterns"],
            top_ctas=trends["top_ctas"],
        )

        try:
            if model == "claude":
                result = await self._generate_with_claude(prompt)
                model_used = "claude-3-opus"
            else:
                result = await self._generate_with_openai(prompt)
                model_used = "gpt-4-turbo"

            generation_time = time.time() - start_time
            return result, generation_time, model_used

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            raise RecommendationError(f"Failed to generate recommendations: {e}") from e

    async def _generate_with_claude(self, prompt: str) -> dict[str, Any]:
        """Generate recommendations using Claude."""
        response = await self.anthropic_client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            system="You are an expert marketing strategist. Analyze competitor ads and generate detailed, actionable content recommendations. Always respond with valid JSON only.",
        )

        result_text = response.content[0].text
        if not result_text:
            raise RecommendationError("Empty response from Claude")

        result_text = result_text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        return json.loads(result_text.strip())

    async def _generate_with_openai(self, prompt: str) -> dict[str, Any]:
        """Generate recommendations using OpenAI."""
        response = await self.openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert marketing strategist. Analyze competitor ads and generate detailed, actionable content recommendations. Always respond with valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=8000,
        )

        result_text = response.choices[0].message.content
        if not result_text:
            raise RecommendationError("Empty response from OpenAI")

        result_text = result_text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        return json.loads(result_text.strip())

    def validate_recommendations(self, recommendations: dict[str, Any]) -> list[str]:
        """
        Validate the generated recommendations structure.

        Args:
            recommendations: Generated recommendations dictionary

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if "recommendations" not in recommendations:
            errors.append("Missing 'recommendations' key")
        elif not isinstance(recommendations["recommendations"], list):
            errors.append("'recommendations' must be a list")
        elif len(recommendations["recommendations"]) == 0:
            errors.append("No recommendations generated")

        if "trend_analysis" not in recommendations:
            errors.append("Missing 'trend_analysis' key")

        for i, rec in enumerate(recommendations.get("recommendations", [])):
            if "concept" not in rec:
                errors.append(f"Recommendation {i+1} missing 'concept'")
            if "priority" not in rec:
                errors.append(f"Recommendation {i+1} missing 'priority'")
            if "ad_format" not in rec:
                errors.append(f"Recommendation {i+1} missing 'ad_format'")

        return errors

    async def regenerate_section(
        self,
        section: str,
        original_recommendations: dict[str, Any],
        feedback: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Regenerate a specific section of recommendations based on feedback.

        Args:
            section: Section to regenerate (e.g., "recommendations", "trend_analysis")
            original_recommendations: Original recommendations
            feedback: User feedback for improvement
            model: Model to use

        Returns:
            Updated recommendations dictionary
        """
        model = model or self.default_model

        prompt = f"""
        The following section of a content recommendation needs improvement based on user feedback.

        SECTION TO IMPROVE: {section}

        ORIGINAL CONTENT:
        {json.dumps(original_recommendations.get(section, {}), indent=2)}

        USER FEEDBACK:
        {feedback}

        Please regenerate this section addressing the feedback while maintaining the same JSON structure.

        Return ONLY valid JSON for the improved section.
        """

        try:
            if model == "claude":
                response = await self.anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}],
                )
                result_text = response.content[0].text
            else:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": "You are an expert marketing strategist."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.5,
                    max_tokens=4000,
                )
                result_text = response.choices[0].message.content

            if not result_text:
                raise RecommendationError("Empty response")

            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            improved_section = json.loads(result_text.strip())

            original_recommendations[section] = improved_section
            return original_recommendations

        except Exception as e:
            logger.error(f"Failed to regenerate section: {e}")
            raise RecommendationError(f"Failed to regenerate section: {e}") from e
