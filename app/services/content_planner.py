"""Content Planning Agent (Writer) for generating visual scripts from recipes and user content."""

import json
import logging
import uuid
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.project import Project
from app.models.recipe import Recipe
from app.models.user_video_segment import UserVideoSegment
from app.models.visual_script import VisualScript
from app.schemas.visual_script import (
    ContentPlanningInput,
    ContentPlanningOutput,
    VisualScriptGenerateRequest,
    VisualScriptResponse,
    VisualScriptSlot,
)
from app.utils.prompts import CONTENT_PLANNING_PROMPT

logger = logging.getLogger(__name__)


class ContentPlanningError(Exception):
    """Exception raised when content planning fails."""

    pass


class ContentPlanningAgent:
    """
    Content Planning Agent (Writer) that generates visual scripts.

    Takes a recipe template + user content summaries + brand context and produces
    a visual script with slots that can be filled by semantic search.
    """

    def __init__(self) -> None:
        """Initialize the content planning agent."""
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4.1-nano"

    async def generate(
        self,
        db: AsyncSession,
        request: VisualScriptGenerateRequest,
    ) -> VisualScriptResponse:
        """
        Generate a visual script from a recipe and project content.

        Args:
            db: Database session
            request: Generation request with project_id, recipe_id, and optional user_prompt

        Returns:
            VisualScriptResponse with the generated script

        Raises:
            ContentPlanningError: If generation fails
        """
        # Fetch project with brand profile
        logger.info(f"[WRITER] Fetching project {request.project_id}...")
        project = await self._get_project(db, request.project_id)

        # Fetch recipe
        logger.info(f"[WRITER] Fetching recipe {request.recipe_id}...")
        recipe = await self._get_recipe(db, request.recipe_id)

        # Fetch user content segments
        logger.info("[WRITER] Fetching project segments...")
        segments = await self._get_project_segments(db, request.project_id)
        logger.info(f"[WRITER] Found {len(segments)} segments")

        # Build planning input
        logger.info("[WRITER] Building planning input...")
        planning_input = self._build_planning_input(
            recipe=recipe,
            segments=segments,
            project=project,
            user_prompt=request.user_prompt,
        )

        # Generate visual script using LLM
        logger.info("[WRITER] Calling LLM to generate visual script...")
        planning_output = await self._generate_script(planning_input)
        logger.info(f"[WRITER] LLM returned {len(planning_output.slots)} slots")

        # Create and store visual script
        visual_script = VisualScript(
            id=uuid.uuid4(),
            project_id=request.project_id,
            recipe_id=request.recipe_id,
            total_duration_seconds=planning_output.total_duration_seconds,
            slots=[slot.model_dump() for slot in planning_output.slots],
            audio_suggestion=planning_output.audio_suggestion,
            pacing_notes=planning_output.pacing_notes,
        )

        db.add(visual_script)
        await db.commit()
        await db.refresh(visual_script)

        logger.info(
            f"Generated visual script {visual_script.id} with {len(planning_output.slots)} slots"
        )

        return VisualScriptResponse(
            id=visual_script.id,
            project_id=visual_script.project_id,
            recipe_id=visual_script.recipe_id,
            total_duration_seconds=visual_script.total_duration_seconds,
            slots=[VisualScriptSlot(**slot) for slot in visual_script.slots],
            audio_suggestion=visual_script.audio_suggestion,
            pacing_notes=visual_script.pacing_notes,
            created_at=visual_script.created_at,
            updated_at=visual_script.updated_at,
        )

    async def _get_project(self, db: AsyncSession, project_id: uuid.UUID) -> Project:
        """Fetch project with brand profile."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise ContentPlanningError(f"Project not found: {project_id}")

        return project

    async def _get_recipe(self, db: AsyncSession, recipe_id: uuid.UUID) -> Recipe:
        """Fetch recipe by ID."""
        result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
        recipe = result.scalar_one_or_none()

        if not recipe:
            raise ContentPlanningError(f"Recipe not found: {recipe_id}")

        return recipe

    async def _get_project_segments(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> list[UserVideoSegment]:
        """Fetch all video segments for a project."""
        result = await db.execute(
            select(UserVideoSegment)
            .where(UserVideoSegment.project_id == project_id)
            .order_by(UserVideoSegment.source_file_name, UserVideoSegment.timestamp_start)
        )
        return list(result.scalars().all())

    def _build_planning_input(
        self,
        recipe: Recipe,
        segments: list[UserVideoSegment],
        project: Project,
        user_prompt: str | None,
    ) -> ContentPlanningInput:
        """Build the input for the content planning prompt."""
        # Parse recipe structure
        recipe_structure = []
        if recipe.structure:
            for beat in recipe.structure:
                if isinstance(beat, dict):
                    recipe_structure.append(beat)
                else:
                    # Handle if stored as BeatDefinition
                    recipe_structure.append(
                        beat.model_dump() if hasattr(beat, "model_dump") else beat
                    )

        # Build content summaries from segments
        content_summaries = []
        for segment in segments:
            summary_parts = [segment.visual_description or ""]
            if segment.action_tags:
                tags = segment.action_tags if isinstance(segment.action_tags, list) else []
                if tags:
                    summary_parts.append(f"Tags: {', '.join(tags)}")
            summary = " | ".join(filter(None, summary_parts))
            if summary:
                content_summaries.append(
                    f"[{segment.source_file_name} @ {segment.timestamp_start:.1f}s-{segment.timestamp_end:.1f}s]: {summary}"
                )

        # Build brand profile dict
        brand_profile = None
        if project.brand_profile:
            bp = project.brand_profile
            brand_profile = {
                "industry": bp.industry,
                "niche": bp.niche,
                "core_offer": bp.core_offer,
                "keywords": bp.keywords,
                "tone": bp.tone,
                "forbidden_terms": bp.forbidden_terms,
            }

        return ContentPlanningInput(
            recipe_name=recipe.name,
            recipe_structure=recipe_structure,
            recipe_pacing=recipe.pacing,
            recipe_style=recipe.style,
            total_target_duration=recipe.total_duration_seconds,
            user_content_summaries=content_summaries,
            user_prompt=user_prompt or project.user_prompt,
            brand_profile=brand_profile,
        )

    async def _generate_script(
        self,
        planning_input: ContentPlanningInput,
    ) -> ContentPlanningOutput:
        """
        Call the LLM to generate the visual script.

        Args:
            planning_input: Assembled input data for the planning prompt

        Returns:
            ContentPlanningOutput with generated slots

        Raises:
            ContentPlanningError: If LLM call or parsing fails
        """
        # Format the prompt
        prompt = CONTENT_PLANNING_PROMPT.format(
            recipe_name=planning_input.recipe_name,
            recipe_style=planning_input.recipe_style or "Not specified",
            recipe_pacing=planning_input.recipe_pacing or "medium",
            total_target_duration=planning_input.total_target_duration or 30,
            recipe_structure=json.dumps(planning_input.recipe_structure, indent=2),
            user_content_summaries=(
                "\n".join(planning_input.user_content_summaries[:50])  # Limit to 50 segments
                if planning_input.user_content_summaries
                else "No content uploaded yet - generate generic search queries"
            ),
            user_prompt=planning_input.user_prompt or "No specific direction - follow the recipe",
            brand_profile=(
                json.dumps(planning_input.brand_profile, indent=2)
                if planning_input.brand_profile
                else "No brand profile - use generic professional tone"
            ),
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert video ad creative director. Generate detailed visual scripts that can be executed with semantic search and video editing.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
            )

            result_text = response.choices[0].message.content
            if not result_text:
                raise ContentPlanningError("Empty response from LLM")

            # Clean markdown if present
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            # Parse JSON
            result = json.loads(result_text)

            # Handle multi-encoded JSON
            max_decode_depth = 5
            decode_attempts = 0
            while isinstance(result, str) and decode_attempts < max_decode_depth:
                result = json.loads(result)
                decode_attempts += 1

            if not isinstance(result, dict):
                raise ContentPlanningError(
                    f"LLM response is not a JSON object. Got: {type(result).__name__}"
                )

            return self._parse_planning_output(result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise ContentPlanningError(f"Failed to parse script: {e}") from e
        except Exception as e:
            logger.error(f"Content planning failed: {e}")
            raise ContentPlanningError(f"Planning failed: {e}") from e

    def _parse_planning_output(self, raw: dict[str, Any]) -> ContentPlanningOutput:
        """Parse raw LLM response into ContentPlanningOutput."""
        slots = []
        for slot_data in raw.get("slots", []):
            slot = VisualScriptSlot(
                id=slot_data.get("id", f"slot_{len(slots) + 1:02d}"),
                beat_type=slot_data.get("beat_type", "Unknown"),
                target_duration=float(slot_data.get("target_duration", 3.0)),
                search_query=slot_data.get("search_query", ""),
                overlay_text=slot_data.get("overlay_text"),
                text_position=slot_data.get("text_position"),
                transition_in=slot_data.get("transition_in"),
                transition_out=slot_data.get("transition_out"),
                notes=slot_data.get("notes"),
                characteristics=slot_data.get("characteristics", []),
                cinematics=slot_data.get("cinematics"),
            )
            slots.append(slot)

        return ContentPlanningOutput(
            slots=slots,
            total_duration_seconds=int(raw.get("total_duration_seconds", 30)),
            audio_suggestion=raw.get("audio_suggestion"),
            pacing_notes=raw.get("pacing_notes"),
            planning_notes=raw.get("planning_notes", []),
        )

    async def get_visual_script(
        self, db: AsyncSession, script_id: uuid.UUID
    ) -> VisualScript | None:
        """Get a visual script by ID."""
        result = await db.execute(select(VisualScript).where(VisualScript.id == script_id))
        return result.scalar_one_or_none()

    async def list_project_scripts(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> list[VisualScript]:
        """List all visual scripts for a project."""
        result = await db.execute(
            select(VisualScript)
            .where(VisualScript.project_id == project_id)
            .order_by(VisualScript.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_visual_script(self, db: AsyncSession, script_id: uuid.UUID) -> bool:
        """Delete a visual script by ID."""
        script = await self.get_visual_script(db, script_id)
        if not script:
            return False
        await db.delete(script)
        await db.commit()
        return True
