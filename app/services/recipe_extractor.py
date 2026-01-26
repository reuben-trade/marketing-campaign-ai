"""Recipe extraction service for converting analyzed ads into structural templates."""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad import Ad
from app.models.ad_element import AdElement
from app.models.recipe import Recipe
from app.schemas.recipe import BeatDefinition, RecipeExtractResponse, RecipeResponse

logger = logging.getLogger(__name__)


class RecipeExtractionError(Exception):
    """Exception raised when recipe extraction fails."""

    pass


class RecipeExtractor:
    """Extracts structural recipes from analyzed competitor ads."""

    # Mapping from production_style in analysis to recipe style
    STYLE_MAPPING = {
        "High-production Studio": "polished",
        "Authentic UGC": "ugc",
        "Hybrid": "ugc",
        "Animation": "animation",
        "Stock Footage Mashup": "polished",
        "Screen Recording": "demo",
        "Talking Head": "talking_head",
        "Documentary Style": "cinematic",
        "Influencer Native": "ugc",
        "Unknown": None,
    }

    # Mapping from pacing score to pacing category
    @staticmethod
    def _score_to_pacing(score: int | None) -> str:
        """Convert pacing score (1-10) to pacing category."""
        if score is None:
            return "medium"
        if score <= 3:
            return "slow"
        if score <= 6:
            return "medium"
        if score <= 8:
            return "fast"
        return "dynamic"

    @staticmethod
    def _parse_timestamp(timestamp: str) -> float:
        """Parse MM:SS or SS timestamp to seconds."""
        if not timestamp:
            return 0.0
        try:
            if ":" in timestamp:
                parts = timestamp.split(":")
                if len(parts) == 2:
                    return float(parts[0]) * 60 + float(parts[1])
                if len(parts) == 3:
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            return float(timestamp)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _calculate_duration(start_time: str, end_time: str) -> float:
        """Calculate duration in seconds from start and end timestamps."""
        start = RecipeExtractor._parse_timestamp(start_time)
        end = RecipeExtractor._parse_timestamp(end_time)
        return max(0.0, end - start)

    def _extract_characteristics(self, beat: dict[str, Any] | AdElement) -> list[str]:
        """Extract visual/audio characteristics from a beat."""
        characteristics = []

        if isinstance(beat, AdElement):
            # From AdElement model
            if beat.cinematic_features:
                characteristics.extend(beat.cinematic_features)
            if beat.camera_angle:
                characteristics.append(beat.camera_angle.lower().replace(" ", "_"))
            if beat.motion_type:
                characteristics.append(beat.motion_type.lower().replace(" ", "_"))
            if beat.text_overlays:
                characteristics.append("text_overlay")
            if beat.emotion_intensity and beat.emotion_intensity >= 7:
                characteristics.append("high_energy")
            elif beat.emotion_intensity and beat.emotion_intensity <= 3:
                characteristics.append("calm")
        else:
            # From raw video_intelligence dict
            cinematics = beat.get("cinematics", {})
            if cinematics.get("cinematic_features"):
                characteristics.extend(cinematics["cinematic_features"])
            if cinematics.get("camera_angle"):
                characteristics.append(cinematics["camera_angle"].lower().replace(" ", "_"))
            if cinematics.get("motion_type"):
                characteristics.append(cinematics["motion_type"].lower().replace(" ", "_"))
            if beat.get("text_overlays_in_beat"):
                characteristics.append("text_overlay")
            if beat.get("emotion_intensity") and beat["emotion_intensity"] >= 7:
                characteristics.append("high_energy")
            elif beat.get("emotion_intensity") and beat["emotion_intensity"] <= 3:
                characteristics.append("calm")

        # Deduplicate and clean
        return list(set(c for c in characteristics if c))

    def _extract_cinematics(self, beat: dict[str, Any] | AdElement) -> dict | None:
        """Extract cinematic details from a beat."""
        if isinstance(beat, AdElement):
            cinematics = {}
            if beat.camera_angle:
                cinematics["camera_angle"] = beat.camera_angle
            if beat.lighting_style:
                cinematics["lighting_style"] = beat.lighting_style
            if beat.color_grading:
                cinematics["color_grading"] = beat.color_grading
            if beat.motion_type:
                cinematics["motion_type"] = beat.motion_type
            return cinematics if cinematics else None
        else:
            raw_cinematics = beat.get("cinematics", {})
            if not raw_cinematics:
                return None
            cinematics = {}
            if raw_cinematics.get("camera_angle"):
                cinematics["camera_angle"] = raw_cinematics["camera_angle"]
            if raw_cinematics.get("lighting_style"):
                cinematics["lighting_style"] = raw_cinematics["lighting_style"]
            if raw_cinematics.get("color_grading"):
                cinematics["color_grading"] = raw_cinematics["color_grading"]
            if raw_cinematics.get("motion_type"):
                cinematics["motion_type"] = raw_cinematics["motion_type"]
            return cinematics if cinematics else None

    def _extract_text_overlay_pattern(self, beat: dict[str, Any] | AdElement) -> str | None:
        """Determine text overlay pattern from a beat."""
        if isinstance(beat, AdElement):
            if not beat.text_overlays:
                return None
            # Analyze overlay purposes
            overlays = beat.text_overlays
        else:
            overlays = beat.get("text_overlays_in_beat", [])
            if not overlays:
                return None

        # Determine pattern based on beat type and overlay content
        beat_type = beat.beat_type if isinstance(beat, AdElement) else beat.get("beat_type", "")
        if beat_type == "Hook":
            return "attention_grabber"
        if beat_type == "CTA":
            return "cta_text"
        if beat_type == "Benefit Stack":
            return "benefit_list"
        if beat_type in ["Problem", "Solution"]:
            return "headline"
        return "general"

    def _infer_purpose(self, beat_type: str) -> str:
        """Infer purpose from beat type."""
        purposes = {
            "Hook": "Stop the scroll and grab attention",
            "Problem": "Identify with viewer's pain point",
            "Solution": "Present the product/service as the answer",
            "Product Showcase": "Demonstrate features and how it works",
            "Social Proof": "Build trust through testimonials/reviews",
            "Benefit Stack": "List value propositions",
            "Objection Handling": "Address doubts and build trust",
            "CTA": "Drive conversion action",
            "Transition": "Bridge between sections",
            "Unknown": "General content",
        }
        return purposes.get(beat_type, "General content")

    def _generate_recipe_name(self, structure: list[BeatDefinition], style: str | None) -> str:
        """Generate a descriptive name for the recipe based on its structure."""
        # Get the main beat types
        beat_types = [b.beat_type for b in structure]

        # Build name from key beats
        key_beats = []
        if "Hook" in beat_types:
            key_beats.append("Hook")
        if "Problem" in beat_types or "Solution" in beat_types:
            key_beats.append("PAS")  # Problem-Agitation-Solution pattern
        elif "Product Showcase" in beat_types:
            key_beats.append("Demo")
        if "Social Proof" in beat_types:
            key_beats.append("Proof")
        if "CTA" in beat_types:
            key_beats.append("CTA")

        if not key_beats:
            key_beats = beat_types[:3]

        name_parts = " + ".join(key_beats)

        # Add style qualifier
        style_qualifier = ""
        if style == "ugc":
            style_qualifier = "UGC "
        elif style == "polished":
            style_qualifier = "Polished "
        elif style == "cinematic":
            style_qualifier = "Cinematic "

        return f"{style_qualifier}{name_parts}"

    async def extract_from_ad(
        self,
        db: AsyncSession,
        ad_id: uuid.UUID,
        custom_name: str | None = None,
    ) -> RecipeExtractResponse:
        """
        Extract a structural recipe from an analyzed ad.

        Args:
            db: Database session
            ad_id: ID of the ad to extract recipe from
            custom_name: Optional custom name for the recipe

        Returns:
            RecipeExtractResponse with the created recipe and extraction notes
        """
        notes: list[str] = []

        # Fetch the ad with its elements
        result = await db.execute(select(Ad).where(Ad.id == ad_id))
        ad = result.scalar_one_or_none()

        if not ad:
            raise RecipeExtractionError(f"Ad with ID {ad_id} not found")

        if not ad.analyzed:
            raise RecipeExtractionError(f"Ad {ad_id} has not been analyzed yet")

        # Determine source of beat data
        timeline = []
        total_duration = None
        pacing_score = None
        production_style = None

        # Prefer video_intelligence (V2 analysis) if available
        if ad.video_intelligence:
            vi = ad.video_intelligence
            timeline = vi.get("timeline", [])
            total_duration = vi.get("platform_optimization", {}).get("duration_seconds")
            pacing_score = vi.get("overall_pacing_score")
            production_style = vi.get("production_style")
            notes.append("Extracted from V2 video_intelligence data")
        elif ad.elements:
            # Fall back to ad_elements table
            timeline = ad.elements
            notes.append("Extracted from ad_elements table")
        else:
            raise RecipeExtractionError(
                f"Ad {ad_id} has no timeline data (no video_intelligence or elements)"
            )

        if not timeline:
            raise RecipeExtractionError(f"Ad {ad_id} has empty timeline")

        # Extract beat definitions
        structure: list[BeatDefinition] = []
        total_calc_duration = 0.0

        for beat in timeline:
            if isinstance(beat, AdElement):
                beat_type = beat.beat_type
                start_time = beat.start_time or "00:00"
                end_time = beat.end_time or "00:00"
                duration = beat.duration_seconds or self._calculate_duration(start_time, end_time)
                rhetorical_mode = beat.rhetorical_mode
                transition_out = beat.transition_out
            else:
                beat_type = beat.get("beat_type", "Unknown")
                start_time = beat.get("start_time", "00:00")
                end_time = beat.get("end_time", "00:00")
                duration = self._calculate_duration(start_time, end_time)
                rhetorical_mode = beat.get("rhetorical_appeal", {}).get("mode")
                cinematics = beat.get("cinematics", {})
                transition_out = cinematics.get("transition_out")

            # Calculate duration range (allow +/- 20% flexibility)
            min_duration = max(0.5, duration * 0.8)
            max_duration = duration * 1.2

            beat_def = BeatDefinition(
                beat_type=beat_type,
                duration_range=[round(min_duration, 1), round(max_duration, 1)],
                characteristics=self._extract_characteristics(beat),
                purpose=self._infer_purpose(beat_type),
                cinematics=self._extract_cinematics(beat),
                rhetorical_mode=rhetorical_mode if rhetorical_mode != "Unknown" else None,
                text_overlay_pattern=self._extract_text_overlay_pattern(beat),
                transition_out=transition_out,
            )
            structure.append(beat_def)
            total_calc_duration += duration

        # Determine style
        style = self.STYLE_MAPPING.get(production_style) if production_style else None

        # Determine pacing
        pacing = self._score_to_pacing(pacing_score)

        # Use provided total_duration or calculated
        if total_duration:
            final_duration = int(total_duration)
        else:
            final_duration = int(total_calc_duration)
            notes.append(f"Duration calculated from beats: {final_duration}s")

        # Generate or use custom name
        name = custom_name or self._generate_recipe_name(structure, style)

        # Create the recipe
        recipe = Recipe(
            id=uuid.uuid4(),
            source_ad_id=ad_id,
            name=name,
            total_duration_seconds=final_duration,
            structure=[b.model_dump() for b in structure],
            pacing=pacing,
            style=style,
            composite_score=ad.composite_score,
        )

        db.add(recipe)
        await db.commit()
        await db.refresh(recipe)

        notes.append(f"Created recipe with {len(structure)} beats")

        return RecipeExtractResponse(
            recipe=RecipeResponse(
                id=recipe.id,
                source_ad_id=recipe.source_ad_id,
                name=recipe.name,
                total_duration_seconds=recipe.total_duration_seconds,
                structure=structure,
                pacing=recipe.pacing,
                style=recipe.style,
                composite_score=recipe.composite_score,
                created_at=recipe.created_at,
            ),
            extraction_notes=notes,
        )

    async def get_recipe(self, db: AsyncSession, recipe_id: uuid.UUID) -> Recipe | None:
        """Get a recipe by ID."""
        result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
        return result.scalar_one_or_none()

    async def list_recipes(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        style: str | None = None,
        pacing: str | None = None,
        min_score: float | None = None,
    ) -> tuple[list[Recipe], int]:
        """
        List recipes with optional filtering.

        Args:
            db: Database session
            limit: Maximum number of recipes to return
            offset: Number of recipes to skip
            style: Filter by style
            pacing: Filter by pacing
            min_score: Minimum composite score

        Returns:
            Tuple of (recipes, total_count)
        """
        query = select(Recipe)

        if style:
            query = query.where(Recipe.style == style)
        if pacing:
            query = query.where(Recipe.pacing == pacing)
        if min_score is not None:
            query = query.where(Recipe.composite_score >= min_score)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(Recipe.composite_score.desc().nullslast(), Recipe.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        recipes = list(result.scalars().all())

        return recipes, total

    async def delete_recipe(self, db: AsyncSession, recipe_id: uuid.UUID) -> bool:
        """Delete a recipe by ID."""
        recipe = await self.get_recipe(db, recipe_id)
        if not recipe:
            return False
        await db.delete(recipe)
        await db.commit()
        return True
