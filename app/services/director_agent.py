"""Director Agent (Assembler) - LLM-based clips-first video assembly.

This agent uses the Viral Director prompt to assemble videos from analyzed clips.
It takes a clips-first approach: load all available clips, send to LLM for creative
direction, then convert the output to a Remotion payload.
"""

import json
import logging
import uuid

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user_video_segment import UserVideoSegment
from app.prompts.director_prompt import get_director_prompt
from app.schemas.director_output import (
    BRollOverlayEntry,
    ClipInfo,
    DirectorInput,
    DirectorLLMOutput,
    GeneratedBRollEntry,
    TextSlideEntry,
    TimelineEntryType,
    TitleCardEntry,
    VideoClipEntry,
)
from app.schemas.remotion_payload import (
    AudioTrack,
    DirectorAgentInput,
    DirectorAgentOutput,
    RemotionPayload,
)
from app.services.director_converter import DirectorConverter

logger = logging.getLogger(__name__)


class DirectorAgentError(Exception):
    """Exception raised when Director Agent fails."""

    pass


class DirectorAgent:
    """
    Director Agent using LLM-based clips-first assembly.

    Instead of semantic search per slot, this agent:
    1. Loads ALL analyzed clips with rich metadata
    2. Sends clip inventory + context to LLM with Viral Director prompt
    3. LLM reasons about story arc, pacing, hooks
    4. LLM outputs timeline JSON
    5. Converts to Remotion payload
    """

    def __init__(self) -> None:
        """Initialize the Director Agent."""
        settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4.1"  # Use GPT-4.1 for best creative output
        self.converter = DirectorConverter()
        self.default_fps = 30

    async def assemble(
        self,
        db: AsyncSession,
        input_data: DirectorAgentInput,
    ) -> DirectorAgentOutput:
        """
        Assemble a video using LLM-based clips-first approach.

        Args:
            db: Database session
            input_data: Assembly configuration

        Returns:
            DirectorAgentOutput with generated payload and stats

        Raises:
            DirectorAgentError: If assembly fails
        """
        logger.info("=" * 60)
        logger.info(f"[DIRECTOR] Starting assembly for project {input_data.project_id}")
        logger.info("=" * 60)

        try:
            # Step 1: Load all clips with V2 metadata
            logger.info("[DIRECTOR] Step 1: Loading clip inventory...")
            clips, file_url_map = await self._load_clip_inventory(db, input_data.project_id)
            logger.info(f"[DIRECTOR] Loaded {len(clips)} clips from {len(file_url_map)} files")

            if not clips:
                raise DirectorAgentError("No analyzed clips found in project")

            # Print clip summary for debugging
            self._print_clip_summary(clips)

            # Step 2: Load project and brand profile
            logger.info("[DIRECTOR] Step 2: Loading project context...")
            project = await self._get_project(db, input_data.project_id)
            brand_profile = self._extract_brand_profile(project)
            logger.info(f"[DIRECTOR] Project: {project.name}")
            if brand_profile:
                logger.info("[DIRECTOR] Brand profile loaded")

            # Step 3: Build and send prompt to LLM
            logger.info("[DIRECTOR] Step 3: Calling LLM with Viral Director prompt...")
            director_input = DirectorInput(
                project_id=input_data.project_id,
                available_clips=[ClipInfo(**c) for c in clips],
                target_duration_seconds=30,  # Default target
                brand_profile=brand_profile,
                user_instructions=project.user_prompt,
            )

            llm_output = await self._call_director_llm(director_input)
            logger.info(
                f"[DIRECTOR] LLM returned timeline with {len(llm_output.timeline)} segments"
            )
            logger.info(f"[DIRECTOR] Total duration: {llm_output.get_total_duration():.1f}s")

            # Print timeline summary
            self._print_timeline_summary(llm_output)

            # Step 4: Convert to Remotion payload
            logger.info("[DIRECTOR] Step 4: Converting to Remotion payload...")

            payload = self.converter.convert(
                llm_output=llm_output,
                project_id=input_data.project_id,
                file_url_lookup=file_url_map,
            )

            # Add audio track if provided
            if input_data.audio_url:
                payload.audio_track = AudioTrack(
                    url=input_data.audio_url,
                    volume=0.8,
                    fade_in_frames=15,
                    fade_out_frames=30,
                )

            # Calculate stats
            stats = self._calculate_stats(llm_output, payload)

            logger.info("=" * 60)
            logger.info("[DIRECTOR] Assembly complete!")
            logger.info(
                f"[DIRECTOR] Segments: {stats['clips_selected']}, Duration: {stats['total_duration_seconds']:.1f}s"
            )
            logger.info(f"[DIRECTOR] Gaps: {stats['gaps_detected']}")
            logger.info("=" * 60)

            return DirectorAgentOutput(
                payload=payload,
                stats=stats,
                success=True,
                error_message=None,
            )

        except Exception as e:
            logger.error(f"[DIRECTOR] Assembly failed: {e}")
            raise DirectorAgentError(f"Assembly failed: {e}") from e

    async def _load_clip_inventory(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> tuple[list[dict], dict[str, str]]:
        """Load all analyzed clips with V2 metadata.

        Returns:
            Tuple of (clips list, file_url_map)
        """
        # Get all segments for the project
        result = await db.execute(
            select(UserVideoSegment)
            .where(UserVideoSegment.project_id == project_id)
            .order_by(UserVideoSegment.source_file_name, UserVideoSegment.timestamp_start)
        )
        segments = list(result.scalars().all())

        # Build file URL map
        file_result = await db.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_id)
        )
        files = list(file_result.scalars().all())
        file_url_map = {}
        for f in files:
            if f.file_url:
                file_url_map[str(f.id)] = f.file_url

        # Convert segments to clip info dicts
        clips = []
        for seg in segments:
            # Get URL from segment or file map
            source_url = seg.source_file_url
            if not source_url and seg.source_file_id:
                source_url = file_url_map.get(str(seg.source_file_id))

            clip = {
                "id": str(seg.id),
                "source_file_name": seg.source_file_name,
                "timestamp_start": seg.timestamp_start,
                "timestamp_end": seg.timestamp_end,
                "duration_seconds": seg.duration_seconds
                or (seg.timestamp_end - seg.timestamp_start),
                "visual_description": seg.visual_description,
                "section_type": seg.section_type,
                "section_label": seg.section_label,
                "attention_score": seg.attention_score,
                "emotion_intensity": seg.emotion_intensity,
                "has_speech": seg.has_speech or False,
                "keywords": seg.keywords or [],
                "detailed_breakdown": seg.detailed_breakdown,
                "segment_index": seg.segment_index or 0,
                "total_segments_in_source": seg.total_segments_in_source or 1,
            }
            clips.append(clip)

            # Also map segment ID to URL for converter
            if source_url:
                file_url_map[str(seg.id)] = source_url

        return clips, file_url_map

    def _print_clip_summary(self, clips: list[dict]) -> None:
        """Print a summary of available clips for debugging."""
        logger.info("[DIRECTOR] --- Clip Inventory ---")
        for i, clip in enumerate(clips[:10]):  # Limit to first 10 for brevity
            attention = clip.get("attention_score", "?")
            section = clip.get("section_type", "unknown")
            duration = clip.get("duration_seconds", 0)
            has_speech = "🎤" if clip.get("has_speech") else "🔇"
            logger.info(
                f"[DIRECTOR]   {i+1}. [{section}] {has_speech} "
                f"attention={attention}/10, {duration:.1f}s"
            )
        if len(clips) > 10:
            logger.info(f"[DIRECTOR]   ... and {len(clips) - 10} more clips")

    async def _get_project(self, db: AsyncSession, project_id: uuid.UUID) -> Project:
        """Fetch project with brand profile."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise DirectorAgentError(f"Project not found: {project_id}")

        return project

    def _extract_brand_profile(self, project: Project) -> dict | None:
        """Extract brand profile dict from project."""
        if not project.brand_profile:
            return None

        bp = project.brand_profile
        return {
            "primary_color": bp.primary_color,
            "font_family": bp.font_family,
            "logo_url": bp.logo_url,
            "forbidden_terms": bp.forbidden_terms,
        }

    async def _call_director_llm(
        self,
        director_input: DirectorInput,
    ) -> DirectorLLMOutput:
        """Call the LLM with the Viral Director prompt.

        Args:
            director_input: Input data for the Director

        Returns:
            Parsed DirectorLLMOutput

        Raises:
            DirectorAgentError: If LLM call or parsing fails
        """
        # Format clips for prompt
        clips_for_prompt = [c.model_dump() for c in director_input.available_clips]

        # Build the prompt
        prompt = get_director_prompt(
            available_clips=clips_for_prompt,
            target_duration_seconds=director_input.target_duration_seconds,
            visual_script=director_input.visual_script,
            brand_profile=director_input.brand_profile,
            user_instructions=director_input.user_instructions,
            srt_content=director_input.srt_content,
        )

        logger.info(f"[DIRECTOR] Prompt length: {len(prompt)} chars")
        logger.info(f"[DIRECTOR] Calling {self.model}...")

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,  # Slightly creative but consistent
                max_tokens=8000,
            )

            result_text = response.choices[0].message.content
            if not result_text:
                raise DirectorAgentError("Empty response from LLM")

            logger.info(f"[DIRECTOR] LLM response length: {len(result_text)} chars")

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

            # Handle multi-encoded JSON (LLM sometimes double-escapes)
            max_decode_depth = 3
            decode_attempts = 0
            while isinstance(result, str) and decode_attempts < max_decode_depth:
                result = json.loads(result)
                decode_attempts += 1

            # Parse into DirectorLLMOutput
            return self._parse_llm_output(result)

        except json.JSONDecodeError as e:
            logger.error(f"[DIRECTOR] Failed to parse LLM JSON: {e}")
            logger.error(f"[DIRECTOR] Raw response: {result_text[:500]}...")
            raise DirectorAgentError(f"Failed to parse LLM response: {e}") from e
        except Exception as e:
            logger.error(f"[DIRECTOR] LLM call failed: {e}")
            raise DirectorAgentError(f"LLM call failed: {e}") from e

    def _parse_llm_output(self, raw: dict) -> DirectorLLMOutput:
        """Parse raw LLM JSON into DirectorLLMOutput.

        This handles flexible parsing since LLMs may not perfectly match schema.
        """
        from app.schemas.director_output import (
            AspectRatio,
            CaptionHighlight,
            DirectorThinkingTrace,
            DirectorVideoSettings,
            GapHandlingOption,
            GapRecommendation,
            MusicMood,
            OverlayPosition,
            TextAnimation,
            TextPosition,
            TitleCardAnimation,
            TitleCardLayout,
            TransitionType,
        )

        # Parse video settings
        vs_raw = raw.get("video_settings", {})
        video_settings = DirectorVideoSettings(
            aspect_ratio=self._safe_enum(
                AspectRatio, vs_raw.get("aspect_ratio"), AspectRatio.VERTICAL_9_16
            ),
            target_duration_seconds=float(vs_raw.get("target_duration_seconds", 30)),
            music_mood=self._safe_enum(MusicMood, vs_raw.get("music_mood"), None),
            primary_color=vs_raw.get("primary_color"),
            font_family=vs_raw.get("font_family"),
        )

        # Parse timeline entries
        timeline = []
        for entry_raw in raw.get("timeline", []):
            entry_type = entry_raw.get("entry_type", "video_clip")

            try:
                if entry_type == "video_clip":
                    entry = VideoClipEntry(
                        start_seconds=float(entry_raw.get("start_seconds", 0)),
                        duration_seconds=min(float(entry_raw.get("duration_seconds", 3)), 10),
                        purpose=entry_raw.get("purpose", ""),
                        transition_in=self._safe_enum(
                            TransitionType, entry_raw.get("transition_in"), TransitionType.CUT
                        ),
                        transition_out=self._safe_enum(
                            TransitionType, entry_raw.get("transition_out"), TransitionType.CUT
                        ),
                        segment_id=entry_raw.get("segment_id", ""),
                        source_start_seconds=float(entry_raw.get("source_start_seconds", 0)),
                        source_end_seconds=float(entry_raw.get("source_end_seconds", 3)),
                        overlay_text=entry_raw.get("overlay_text"),
                        overlay_position=self._safe_enum(
                            TextPosition, entry_raw.get("overlay_position"), TextPosition.CENTER
                        ),
                        overlay_animation=self._safe_enum(
                            TextAnimation, entry_raw.get("overlay_animation"), TextAnimation.POP_IN
                        ),
                    )
                elif entry_type == "broll_overlay":
                    entry = BRollOverlayEntry(
                        start_seconds=float(entry_raw.get("start_seconds", 0)),
                        duration_seconds=min(float(entry_raw.get("duration_seconds", 3)), 10),
                        purpose=entry_raw.get("purpose", ""),
                        transition_in=self._safe_enum(
                            TransitionType, entry_raw.get("transition_in"), TransitionType.CUT
                        ),
                        transition_out=self._safe_enum(
                            TransitionType, entry_raw.get("transition_out"), TransitionType.CUT
                        ),
                        main_segment_id=entry_raw.get("main_segment_id", ""),
                        main_source_start_seconds=float(
                            entry_raw.get("main_source_start_seconds", 0)
                        ),
                        main_source_end_seconds=float(entry_raw.get("main_source_end_seconds", 3)),
                        overlay_segment_id=entry_raw.get("overlay_segment_id", ""),
                        overlay_source_start_seconds=float(
                            entry_raw.get("overlay_source_start_seconds", 0)
                        ),
                        overlay_source_end_seconds=float(
                            entry_raw.get("overlay_source_end_seconds", 3)
                        ),
                        overlay_start_offset_seconds=float(
                            entry_raw.get("overlay_start_offset_seconds", 0)
                        ),
                        overlay_duration_seconds=entry_raw.get("overlay_duration_seconds"),
                        overlay_position=self._safe_enum(
                            OverlayPosition, entry_raw.get("overlay_position"), OverlayPosition.FULL
                        ),
                        overlay_opacity=float(entry_raw.get("overlay_opacity", 1.0)),
                    )
                elif entry_type == "title_card":
                    entry = TitleCardEntry(
                        start_seconds=float(entry_raw.get("start_seconds", 0)),
                        duration_seconds=min(float(entry_raw.get("duration_seconds", 3)), 10),
                        purpose=entry_raw.get("purpose", ""),
                        transition_in=self._safe_enum(
                            TransitionType, entry_raw.get("transition_in"), TransitionType.CUT
                        ),
                        transition_out=self._safe_enum(
                            TransitionType, entry_raw.get("transition_out"), TransitionType.CUT
                        ),
                        headline=entry_raw.get("headline", ""),
                        subheadline=entry_raw.get("subheadline"),
                        tagline=entry_raw.get("tagline"),
                        background_color=entry_raw.get("background_color", "#1a1a2e"),
                        text_color=entry_raw.get("text_color", "#FFFFFF"),
                        accent_color=entry_raw.get("accent_color"),
                        animation=self._safe_enum(
                            TitleCardAnimation,
                            entry_raw.get("animation"),
                            TitleCardAnimation.FADE_UP,
                        ),
                        layout=self._safe_enum(
                            TitleCardLayout, entry_raw.get("layout"), TitleCardLayout.CENTERED
                        ),
                        show_logo=entry_raw.get("show_logo", True),
                    )
                elif entry_type == "text_slide":
                    entry = TextSlideEntry(
                        start_seconds=float(entry_raw.get("start_seconds", 0)),
                        duration_seconds=min(float(entry_raw.get("duration_seconds", 3)), 10),
                        purpose=entry_raw.get("purpose", ""),
                        transition_in=self._safe_enum(
                            TransitionType, entry_raw.get("transition_in"), TransitionType.CUT
                        ),
                        transition_out=self._safe_enum(
                            TransitionType, entry_raw.get("transition_out"), TransitionType.CUT
                        ),
                        headline=entry_raw.get("headline", ""),
                        subheadline=entry_raw.get("subheadline"),
                        background_color=entry_raw.get("background_color", "#1a1a2e"),
                        text_color=entry_raw.get("text_color", "#FFFFFF"),
                    )
                elif entry_type == "generated_broll":
                    entry = GeneratedBRollEntry(
                        start_seconds=float(entry_raw.get("start_seconds", 0)),
                        duration_seconds=min(float(entry_raw.get("duration_seconds", 3)), 10),
                        purpose=entry_raw.get("purpose", ""),
                        transition_in=self._safe_enum(
                            TransitionType, entry_raw.get("transition_in"), TransitionType.CUT
                        ),
                        transition_out=self._safe_enum(
                            TransitionType, entry_raw.get("transition_out"), TransitionType.CUT
                        ),
                        generation_prompt=entry_raw.get("generation_prompt", ""),
                        overlay_text=entry_raw.get("overlay_text"),
                        overlay_position=self._safe_enum(
                            TextPosition, entry_raw.get("overlay_position"), TextPosition.CENTER
                        ),
                    )
                else:
                    logger.warning(f"[DIRECTOR] Unknown entry type: {entry_type}, skipping")
                    continue

                timeline.append(entry)
            except Exception as e:
                logger.warning(f"[DIRECTOR] Failed to parse timeline entry: {e}")
                continue

        if not timeline:
            raise DirectorAgentError("No valid timeline entries parsed from LLM output")

        # Parse gaps
        gaps = []
        for gap_raw in raw.get("gaps", []):
            try:
                gap = GapRecommendation(
                    gap_id=gap_raw.get("gap_id", f"gap_{len(gaps)}"),
                    position_seconds=float(gap_raw.get("position_seconds", 0)),
                    duration_seconds=float(gap_raw.get("duration_seconds", 3)),
                    reason=gap_raw.get("reason", "Unknown"),
                    beat_type=gap_raw.get("beat_type"),
                    recommended_action=self._safe_enum(
                        GapHandlingOption,
                        gap_raw.get("recommended_action"),
                        GapHandlingOption.GENERATE_BROLL,
                    ),
                    broll_prompt=gap_raw.get("broll_prompt"),
                    search_query_suggestion=gap_raw.get("search_query_suggestion"),
                )
                gaps.append(gap)
            except Exception as e:
                logger.warning(f"[DIRECTOR] Failed to parse gap: {e}")

        # Parse caption highlights
        highlights = []
        for h_raw in raw.get("caption_highlights", []):
            try:
                highlight = CaptionHighlight(
                    word=h_raw.get("word", ""),
                    highlight_color=h_raw.get("highlight_color", "#FFD700"),
                    is_power_word=h_raw.get("is_power_word", False),
                )
                highlights.append(highlight)
            except Exception:
                pass

        # Parse thinking trace
        thinking_trace = None
        if "thinking_trace" in raw and raw["thinking_trace"]:
            tt = raw["thinking_trace"]
            thinking_trace = DirectorThinkingTrace(
                hook_analysis=tt.get("hook_analysis"),
                story_arc=tt.get("story_arc"),
                pacing_decisions=tt.get("pacing_decisions"),
                clip_selection_rationale=tt.get("clip_selection_rationale", []),
                cta_strategy=tt.get("cta_strategy"),
                gaps_identified=tt.get("gaps_identified", []),
            )

        return DirectorLLMOutput(
            video_settings=video_settings,
            timeline=timeline,
            gaps=gaps,
            caption_highlights=highlights,
            thinking_trace=thinking_trace,
        )

    def _safe_enum(self, enum_class, value, default):
        """Safely parse an enum value with fallback to default."""
        if value is None:
            return default
        try:
            return enum_class(value)
        except (ValueError, KeyError):
            return default

    def _print_timeline_summary(self, llm_output: DirectorLLMOutput) -> None:
        """Print timeline summary for debugging."""
        logger.info("[DIRECTOR] --- Generated Timeline ---")
        for i, entry in enumerate(llm_output.timeline):
            entry_type = entry.entry_type.value
            start = entry.start_seconds
            duration = entry.duration_seconds
            purpose = entry.purpose[:40] if entry.purpose else ""
            logger.info(
                f"[DIRECTOR]   {i+1}. [{entry_type}] {start:.1f}s-{start+duration:.1f}s: {purpose}"
            )

        if llm_output.gaps:
            logger.info(f"[DIRECTOR] --- Gaps ({len(llm_output.gaps)}) ---")
            for gap in llm_output.gaps:
                logger.info(f"[DIRECTOR]   - {gap.reason} at {gap.position_seconds}s")

    def _calculate_stats(
        self,
        llm_output: DirectorLLMOutput,
        payload: RemotionPayload,
    ) -> dict:
        """Calculate assembly statistics."""
        video_clips = sum(
            1
            for e in llm_output.timeline
            if e.entry_type in (TimelineEntryType.VIDEO_CLIP, TimelineEntryType.BROLL_OVERLAY)
        )

        return {
            "total_slots": len(llm_output.timeline),
            "clips_selected": video_clips,
            "gaps_detected": len(llm_output.gaps),
            "coverage_percentage": (video_clips / len(llm_output.timeline) * 100)
            if llm_output.timeline
            else 0,
            "average_similarity": 0,  # Not applicable for LLM-based approach
            "total_duration_seconds": llm_output.get_total_duration(),
            "total_frames": payload.duration_in_frames,
        }


# =============================================================================
# Legacy compatibility - keep the old interface for now
# =============================================================================


async def get_clip_alternatives(
    db: AsyncSession,
    project_id: uuid.UUID,
    slot_id: str,
    search_query: str,
    limit: int = 10,
) -> list[dict]:
    """
    Get alternative clips for a slot (for the replacement UI).

    This is a legacy function that can still be used for clip swapping.
    """
    from app.services.semantic_search_service import SemanticSearchService

    search_service = SemanticSearchService()
    results = await search_service.search_project_segments(
        db=db,
        project_id=project_id,
        query=search_query,
        limit=limit,
        min_similarity=0.3,
    )

    # Build file URL map
    file_result = await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id))
    files = list(file_result.scalars().all())
    file_url_map = {f.id: f.file_url for f in files if f.file_url}

    alternatives = []
    for segment, similarity in results:
        source_url = segment.source_file_url or file_url_map.get(segment.source_file_id)
        alternatives.append(
            {
                "segment_id": str(segment.id),
                "source_file_url": source_url,
                "source_file_name": segment.source_file_name,
                "timestamp_start": segment.timestamp_start,
                "timestamp_end": segment.timestamp_end,
                "duration": segment.duration_seconds,
                "similarity_score": similarity,
                "visual_description": segment.visual_description,
                "action_tags": segment.action_tags,
                "thumbnail_url": segment.thumbnail_url,
            }
        )

    return alternatives
