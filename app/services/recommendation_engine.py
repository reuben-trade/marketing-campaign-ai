"""Recommendation engine for generating content recommendations."""

import json
import logging
import time
from collections import Counter
from typing import Any

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
        """
        Prepare ads analysis for the prompt with rich video_intelligence data.

        Extracts detailed information from the new database schema including:
        - Narrative beats (timeline with beat types, descriptions, transcripts)
        - On-screen text/copy analysis
        - Audio/narration details
        - Cinematics (camera angles, lighting, color grading)
        - Engagement predictors and critique
        """
        summarized_ads = []
        for ad in ads:
            # Get the rich video_intelligence data if available
            video_intel = ad.get("video_intelligence", {}) or {}
            analysis = ad.get("analysis", {}) or {}
            elements = ad.get("elements", []) or []
            creative_analysis = ad.get("creative_analysis", {}) or {}

            # Build comprehensive ad summary
            ad_summary: dict[str, Any] = {
                "ad_id": str(ad.get("id", "")),
                "competitor": ad.get("competitor_name", "Unknown"),
                "creative_type": ad.get("creative_type", "unknown"),
                "engagement": {
                    "likes": ad.get("likes", 0),
                    "comments": ad.get("comments", 0),
                    "shares": ad.get("shares", 0),
                    "total": ad.get("likes", 0) + ad.get("comments", 0) + ad.get("shares", 0),
                },
            }

            # If we have video_intelligence (V2 analysis), use that
            if video_intel:
                ad_summary["creative_dna"] = {
                    "inferred_audience": video_intel.get("inferred_audience", ""),
                    "primary_messaging_pillar": video_intel.get("primary_messaging_pillar", ""),
                    "production_style": video_intel.get("production_style", ""),
                    "hook_score": video_intel.get("hook_score", 5),
                    "overall_pacing_score": video_intel.get("overall_pacing_score", 5),
                    "overall_narrative_summary": video_intel.get("overall_narrative_summary", ""),
                }

                # Extract narrative beats/timeline
                timeline = video_intel.get("timeline", [])
                if timeline:
                    ad_summary["narrative_structure"] = []
                    for beat in timeline:
                        beat_summary = {
                            "beat_type": beat.get("beat_type", "Unknown"),
                            "timing": f"{beat.get('start_time', '00:00')}-{beat.get('end_time', '00:00')}",
                            "visual_description": beat.get("visual_description", ""),
                            "audio_transcript": beat.get("audio_transcript", ""),
                            "tone": beat.get("tone_of_voice", ""),
                            "emotion": beat.get("emotion", ""),
                            "emotion_intensity": beat.get("emotion_intensity", 5),
                        }

                        # Include cinematics
                        cinematics = beat.get("cinematics", {})
                        if cinematics:
                            beat_summary["cinematics"] = {
                                "camera_angle": cinematics.get("camera_angle", ""),
                                "lighting": cinematics.get("lighting_style", ""),
                                "color_grading": cinematics.get("color_grading", ""),
                                "motion": cinematics.get("motion_type", ""),
                            }

                        # Include text overlays in this beat
                        text_overlays = beat.get("text_overlays_in_beat", [])
                        if text_overlays:
                            beat_summary["on_screen_text"] = [
                                {
                                    "text": t.get("text", ""),
                                    "purpose": t.get("purpose", ""),
                                    "position": t.get("position", ""),
                                }
                                for t in text_overlays
                            ]

                        # Include rhetorical appeal
                        rhetorical = beat.get("rhetorical_appeal", {})
                        if rhetorical:
                            beat_summary["rhetorical"] = {
                                "mode": rhetorical.get("mode", ""),
                                "persuasion_techniques": rhetorical.get(
                                    "persuasion_techniques", []
                                ),
                            }

                        ad_summary["narrative_structure"].append(beat_summary)

                # Extract copy analysis
                copy_analysis = video_intel.get("copy_analysis", {})
                if copy_analysis:
                    ad_summary["copy_analysis"] = {
                        "headline": copy_analysis.get("headline_text", ""),
                        "cta_text": copy_analysis.get("cta_text", ""),
                        "copy_framework": copy_analysis.get("copy_framework", ""),
                        "power_words": copy_analysis.get("power_words", []),
                        "word_count": copy_analysis.get("word_count", 0),
                    }
                    # All text overlays
                    all_text = copy_analysis.get("all_text_overlays", [])
                    if all_text:
                        ad_summary["all_on_screen_text"] = [
                            t.get("text", "") for t in all_text if t.get("text")
                        ]

                # Extract audio/narration analysis
                audio_analysis = video_intel.get("audio_analysis", {})
                if audio_analysis:
                    voice = audio_analysis.get("voice", {})
                    music = audio_analysis.get("music", {})
                    ad_summary["audio"] = {
                        "has_voiceover": voice.get("has_voiceover", False),
                        "voice_tone": voice.get("voice_tone", ""),
                        "voice_gender": voice.get("voice_gender", ""),
                        "estimated_wpm": voice.get("estimated_wpm", 0),
                        "has_music": music.get("has_music", False),
                        "music_genre": music.get("genre", ""),
                        "music_energy": music.get("energy_level", ""),
                        "sound_off_compatible": audio_analysis.get("sound_off_compatible", False),
                    }

                # Extract engagement predictors
                engagement_pred = video_intel.get("engagement_predictors", {})
                if engagement_pred:
                    thumb_stop = engagement_pred.get("thumb_stop", {})
                    ad_summary["engagement_factors"] = {
                        "thumb_stop_score": thumb_stop.get("thumb_stop_score", 5),
                        "pattern_interrupt": thumb_stop.get("pattern_interrupt_type", ""),
                        "curiosity_gap": thumb_stop.get("curiosity_gap", False),
                        "uses_social_proof": engagement_pred.get(
                            "uses_social_proof_signals", False
                        ),
                        "uses_fomo": engagement_pred.get("uses_fear_of_missing_out", False),
                        "uses_transformation": engagement_pred.get(
                            "uses_transformation_narrative", False
                        ),
                    }

                # Extract critique insights
                critique = video_intel.get("critique", {})
                if critique:
                    ad_summary["critique"] = {
                        "overall_grade": critique.get("overall_grade", ""),
                        "overall_assessment": critique.get("overall_assessment", ""),
                        "strengths": [s.get("strength", "") for s in critique.get("strengths", [])],
                        "weaknesses": [
                            w.get("weakness", "") for w in critique.get("weaknesses", [])
                        ],
                        "quick_wins": critique.get("quick_wins", []),
                    }

                # Platform optimization
                platform = video_intel.get("platform_optimization", {})
                if platform:
                    ad_summary["platform"] = {
                        "aspect_ratio": platform.get("aspect_ratio", ""),
                        "duration_seconds": platform.get("duration_seconds", 0),
                        "optimal_platforms": platform.get("optimal_platforms", []),
                        "native_feel_score": platform.get("native_feel_score", 5),
                    }

            # If we have ad_elements (individual beats stored in DB), use those
            elif elements:
                ad_summary["narrative_structure"] = []
                for elem in elements:
                    beat_summary = {
                        "beat_type": elem.get("beat_type", "Unknown"),
                        "timing": f"{elem.get('start_time', '00:00')}-{elem.get('end_time', '00:00')}",
                        "visual_description": elem.get("visual_description", ""),
                        "audio_transcript": elem.get("audio_transcript", ""),
                        "tone": elem.get("tone_of_voice", ""),
                        "emotion": elem.get("emotion", ""),
                        "emotion_intensity": elem.get("emotion_intensity", 5),
                        "cinematics": {
                            "camera_angle": elem.get("camera_angle", ""),
                            "lighting": elem.get("lighting_style", ""),
                            "color_grading": elem.get("color_grading", ""),
                            "motion": elem.get("motion_type", ""),
                        },
                        "on_screen_text": elem.get("text_overlays", []),
                        "rhetorical": {
                            "mode": elem.get("rhetorical_mode", ""),
                            "persuasion_techniques": elem.get("persuasion_techniques", []),
                        },
                    }
                    ad_summary["narrative_structure"].append(beat_summary)

            # If we have creative_analysis (denormalized queryable data), add key metrics
            if creative_analysis:
                if "creative_dna" not in ad_summary:
                    ad_summary["creative_dna"] = {}
                ad_summary["creative_dna"].update(
                    {
                        "hook_score": creative_analysis.get("hook_score", 5),
                        "copy_framework": creative_analysis.get("copy_framework", ""),
                        "headline": creative_analysis.get("headline_text", ""),
                        "cta": creative_analysis.get("cta_text", ""),
                        "production_quality": creative_analysis.get("production_quality_score", 5),
                        "thumb_stop_score": creative_analysis.get("thumb_stop_score", 5),
                        "overall_grade": creative_analysis.get("overall_grade", ""),
                    }
                )

            # Fallback to basic analysis if no rich data
            if "creative_dna" not in ad_summary and analysis:
                ad_summary["analysis"] = {
                    "summary": analysis.get("summary", ""),
                    "uvps": analysis.get("uvps", []),
                    "ctas": analysis.get("ctas", []),
                    "visual_themes": analysis.get("visual_themes", []),
                    "emotional_appeal": analysis.get("emotional_appeal", ""),
                    "marketing_effectiveness": analysis.get("marketing_effectiveness", {}),
                    "strategic_insights": analysis.get("strategic_insights", ""),
                }

            summarized_ads.append(ad_summary)

        return json.dumps(summarized_ads, indent=2, default=str)

    def _prepare_user_ad_context(self, user_ad: dict[str, Any]) -> str:
        """
        Prepare user's own ad analysis for comparison in recommendations.

        Uses the same format as competitor ads but marks it as the user's ad.
        """
        user_ad["is_user_ad"] = True
        user_ad["competitor_name"] = "YOUR AD"

        # Use the same rich data extraction
        ads_context = self._prepare_ads_analysis_context([user_ad])
        return ads_context

    def _extract_trends(self, ads: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract trend data from analyzed ads including rich video_intelligence data."""
        visual_themes: list[str] = []
        ctas: list[str] = []
        emotional_appeals: list[str] = []
        production_styles: list[str] = []
        copy_frameworks: list[str] = []
        beat_types: list[str] = []
        total_engagement = 0

        for ad in ads:
            # Check for video_intelligence first
            video_intel = ad.get("video_intelligence", {}) or {}
            analysis = ad.get("analysis", {}) or {}
            creative_analysis = ad.get("creative_analysis", {}) or {}

            if video_intel:
                # Extract from V2 analysis
                if video_intel.get("production_style"):
                    production_styles.append(video_intel["production_style"])

                # Extract copy framework
                copy_analysis = video_intel.get("copy_analysis", {})
                if copy_analysis.get("copy_framework"):
                    copy_frameworks.append(copy_analysis["copy_framework"])
                if copy_analysis.get("cta_text"):
                    ctas.append(copy_analysis["cta_text"])

                # Extract beat types from timeline
                timeline = video_intel.get("timeline", [])
                for beat in timeline:
                    if beat.get("beat_type"):
                        beat_types.append(beat["beat_type"])
                    if beat.get("emotion"):
                        emotional_appeals.append(beat["emotion"])

                # Extract from engagement predictors
                engagement_pred = video_intel.get("engagement_predictors", {})
                thumb_stop = engagement_pred.get("thumb_stop", {})
                if thumb_stop.get("pattern_interrupt_type"):
                    visual_themes.append(thumb_stop["pattern_interrupt_type"])

            elif creative_analysis:
                if creative_analysis.get("copy_framework"):
                    copy_frameworks.append(creative_analysis["copy_framework"])
                if creative_analysis.get("cta_text"):
                    ctas.append(creative_analysis["cta_text"])
                if creative_analysis.get("production_style"):
                    production_styles.append(creative_analysis["production_style"])

            # Fallback to basic analysis
            if analysis:
                visual_themes.extend(analysis.get("visual_themes", []))
                ctas.extend(analysis.get("ctas", []))
                if analysis.get("emotional_appeal"):
                    emotional_appeals.append(analysis["emotional_appeal"])

            total_engagement += ad.get("likes", 0) + ad.get("comments", 0) + ad.get("shares", 0)

        avg_engagement = total_engagement / len(ads) if ads else 0

        theme_counts = Counter(visual_themes)
        cta_counts = Counter(ctas)
        production_counts = Counter(production_styles)
        framework_counts = Counter(copy_frameworks)
        beat_counts = Counter(beat_types)

        return {
            "total_ads": len(ads),
            "avg_engagement": round(avg_engagement, 2),
            "visual_themes": ", ".join([t for t, _ in theme_counts.most_common(5)]),
            "messaging_patterns": ", ".join(
                [e for e, _ in Counter(emotional_appeals).most_common(3)]
            ),
            "top_ctas": ", ".join([c for c, _ in cta_counts.most_common(5)]),
            "production_styles": ", ".join([p for p, _ in production_counts.most_common(3)]),
            "copy_frameworks": ", ".join([f for f, _ in framework_counts.most_common(3)]),
            "common_beat_types": ", ".join([b for b, _ in beat_counts.most_common(5)]),
        }

    async def generate_recommendations(
        self,
        business_strategy: dict[str, Any],
        analyzed_ads: list[dict[str, Any]],
        model: str | None = None,
        num_video_ideas: int = 2,
        num_image_ideas: int = 1,
        user_ad_analysis: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], float, str]:
        """
        Generate content recommendations based on strategy and ad analysis.

        Args:
            business_strategy: Business strategy dictionary
            analyzed_ads: List of analyzed ad dictionaries with video_intelligence
            model: Model to use ("claude" or "openai"), defaults to config
            num_video_ideas: Number of video content ideas to generate
            num_image_ideas: Number of image content ideas to generate
            user_ad_analysis: Optional analysis of user's own ad for comparison

        Returns:
            Tuple of (recommendations dict, generation time in seconds, model used)
        """
        model = model or self.default_model
        start_time = time.time()

        strategy_context = self._prepare_business_strategy_context(business_strategy)
        ads_context = self._prepare_ads_analysis_context(analyzed_ads)
        trends = self._extract_trends(analyzed_ads)

        # Prepare user ad context if provided
        user_ad_context = ""
        if user_ad_analysis:
            user_ad_context = f"""

USER'S CURRENT AD ANALYSIS:
{self._prepare_user_ad_context(user_ad_analysis)}

IMPORTANT: Compare the user's ad against competitor ads and provide specific recommendations
for improvement based on what's working well in competitor ads. Highlight what the user is
doing well and what needs improvement.
"""

        # Build content requirements
        content_requirements = f"""
CONTENT GENERATION REQUIREMENTS:
- Generate exactly {num_video_ideas} VIDEO ad concept(s)
- Generate exactly {num_image_ideas} IMAGE ad concept(s)
- Total recommendations: {num_video_ideas + num_image_ideas}
"""

        prompt = RECOMMENDATION_GENERATION_PROMPT.format(
            business_strategy=strategy_context,
            ads_analysis=ads_context,
            total_ads=trends["total_ads"],
            avg_engagement=trends["avg_engagement"],
            visual_themes=trends["visual_themes"],
            messaging_patterns=trends["messaging_patterns"],
            top_ctas=trends["top_ctas"],
        )

        # Add content requirements and user ad context to the prompt
        prompt = prompt + content_requirements + user_ad_context

        # Add additional trend info for richer context
        if trends.get("production_styles"):
            prompt += f"\n- Common production styles: {trends['production_styles']}"
        if trends.get("copy_frameworks"):
            prompt += f"\n- Effective copy frameworks: {trends['copy_frameworks']}"
        if trends.get("common_beat_types"):
            prompt += f"\n- Common narrative beats: {trends['common_beat_types']}"

        try:
            if model == "claude":
                result = await self._generate_with_claude(prompt)
                model_used = "claude-3-opus"
            else:
                result = await self._generate_with_openai(prompt)
                model_used = "gpt-4o-mini"

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

        result = json.loads(result_text.strip())
        return self._normalize_recommendations(result)

    async def _generate_with_openai(self, prompt: str) -> dict[str, Any]:
        """Generate recommendations using OpenAI."""
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
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
        print("Result text: ", result_text, "\n")
        if not result_text:
            raise RecommendationError("Empty response from OpenAI")

        result_text = result_text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        result = json.loads(result_text.strip())
        return self._normalize_recommendations(result)

    def _normalize_recommendations(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize LLM response to match expected Pydantic schema.

        This handles cases where the LLM returns simplified structures
        instead of the full nested objects expected by the schema.
        """
        if "recommendations" not in data:
            return data

        for rec in data.get("recommendations", []):
            # Normalize copywriting fields for image ads
            if "copywriting" in rec and rec["copywriting"]:
                copywriting = rec["copywriting"]
                for field in ["headline", "subheadline", "body_copy", "cta_button"]:
                    if field in copywriting:
                        value = copywriting[field]
                        # If it's a string, convert to CopyElement structure
                        if isinstance(value, str):
                            copywriting[field] = {
                                "text": value,
                                "placement": "center" if field == "headline" else "below headline",
                            }
                        # If it's a dict but missing required fields, add defaults
                        elif isinstance(value, dict):
                            if "text" not in value:
                                value["text"] = str(value.get("content", ""))
                            if "placement" not in value:
                                value["placement"] = "center" if field == "headline" else "below"

            # Normalize content_breakdown fields for image ads
            if "content_breakdown" in rec and rec["content_breakdown"]:
                content_breakdown = rec["content_breakdown"]
                for field in ["left_side_problem", "right_side_solution"]:
                    if field in content_breakdown:
                        value = content_breakdown[field]
                        # If it's a string, convert to ContentSection structure
                        if isinstance(value, str):
                            content_breakdown[field] = {
                                "visual": value,
                                "text": "",
                                "style": "bold",
                            }
                        # If it's a dict but missing required fields, add defaults
                        elif isinstance(value, dict):
                            if "visual" not in value:
                                value["visual"] = str(value.get("description", ""))
                            if "text" not in value:
                                value["text"] = ""
                            if "style" not in value:
                                value["style"] = "bold"

            # Normalize design_specifications
            if "design_specifications" in rec and rec["design_specifications"]:
                specs = rec["design_specifications"]
                # Ensure colors is a dict if present
                if "colors" in specs and not isinstance(specs["colors"], dict):
                    if isinstance(specs["colors"], list):
                        specs["colors"] = {f"color_{i}": c for i, c in enumerate(specs["colors"])}
                    elif isinstance(specs["colors"], str):
                        specs["colors"] = {"primary": specs["colors"]}

            # Normalize production_notes
            if "production_notes" in rec and rec["production_notes"]:
                notes = rec["production_notes"]
                # Ensure assets_needed is a list
                if "assets_needed" in notes and not isinstance(notes["assets_needed"], list):
                    if isinstance(notes["assets_needed"], str):
                        notes["assets_needed"] = [notes["assets_needed"]]

            # Normalize visual_direction.color_palette
            if "visual_direction" in rec and rec["visual_direction"]:
                vd = rec["visual_direction"]
                if "color_palette" in vd and vd["color_palette"]:
                    cp = vd["color_palette"]
                    # Ensure required fields exist
                    if isinstance(cp, dict):
                        if "primary" not in cp:
                            cp["primary"] = cp.get("main", "#000000")
                        if "secondary" not in cp:
                            cp["secondary"] = cp.get("accent", "#333333")
                        if "accent" not in cp:
                            cp["accent"] = cp.get("highlight", "#666666")

            # Normalize testing_variants - ensure it's a list
            if "testing_variants" in rec:
                if rec["testing_variants"] is None:
                    rec["testing_variants"] = []
                elif not isinstance(rec["testing_variants"], list):
                    rec["testing_variants"] = [rec["testing_variants"]]

            # Normalize success_metrics.secondary - ensure it's a list
            if "success_metrics" in rec and rec["success_metrics"]:
                sm = rec["success_metrics"]
                if "secondary" in sm and not isinstance(sm["secondary"], list):
                    if isinstance(sm["secondary"], str):
                        sm["secondary"] = [sm["secondary"]]
                    elif sm["secondary"] is None:
                        sm["secondary"] = []

        return data

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
                errors.append(f"Recommendation {i + 1} missing 'concept'")
            if "priority" not in rec:
                errors.append(f"Recommendation {i + 1} missing 'priority'")
            if "ad_format" not in rec:
                errors.append(f"Recommendation {i + 1} missing 'ad_format'")

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
                    model="gpt-4o-mini",
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
