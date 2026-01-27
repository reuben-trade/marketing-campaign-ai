"""Director Agent (Assembler) for selecting clips and generating Remotion payload."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user_video_segment import UserVideoSegment
from app.models.visual_script import VisualScript
from app.schemas.remotion_payload import (
    AudioTrack,
    BrandProfile,
    ClipSelectionResult,
    CompositionType,
    DirectorAgentInput,
    DirectorAgentOutput,
    GeneratedBRollSource,
    RemotionPayload,
    SegmentType,
    TextAnimation,
    TextOverlay,
    TextPosition,
    TextSlideContent,
    TimelineSegment,
    Transition,
    TransitionType,
    VideoClipSource,
)
from app.schemas.visual_script import VisualScriptSlot
from app.services.semantic_search_service import SemanticSearchService

logger = logging.getLogger(__name__)


class DirectorAgentError(Exception):
    """Exception raised when Director Agent fails."""

    pass


# Composition dimensions
COMPOSITION_DIMENSIONS = {
    CompositionType.VERTICAL: (1080, 1920),  # 9:16
    CompositionType.HORIZONTAL: (1920, 1080),  # 16:9
    CompositionType.SQUARE: (1080, 1080),  # 1:1
}


class DirectorAgent:
    """
    Director Agent (Assembler) that selects clips and generates Remotion payload.

    Responsibilities:
    1. Select the best clip for each slot based on similarity scores and duration
    2. Detect gaps where no suitable clip exists
    3. Handle gaps with B-Roll generation prompts or text slides
    4. Generate Remotion-compatible timeline payload
    5. Track alternative clips for user replacement UI
    """

    def __init__(self) -> None:
        """Initialize the Director Agent."""
        self.semantic_search = SemanticSearchService()
        self.default_fps = 30

    async def assemble(
        self,
        db: AsyncSession,
        input_data: DirectorAgentInput,
    ) -> DirectorAgentOutput:
        """
        Assemble a Remotion payload from a visual script.

        Args:
            db: Database session
            input_data: Assembly configuration

        Returns:
            DirectorAgentOutput with generated payload and stats

        Raises:
            DirectorAgentError: If assembly fails
        """
        try:
            # Fetch visual script
            visual_script = await self._get_visual_script(db, input_data.visual_script_id)

            # Fetch project with brand profile
            project = await self._get_project(db, input_data.project_id)

            # Build file URL map for segments
            file_url_map = await self._build_file_url_map(db, input_data.project_id)

            # Search for clips for each slot
            slots = [VisualScriptSlot(**slot) for slot in visual_script.slots]
            search_results = await self.semantic_search.search_slots_in_project(
                db=db,
                project_id=input_data.project_id,
                slots=[slot.model_dump() for slot in slots],
                limit_per_slot=5,
                min_similarity=input_data.min_similarity_threshold,
            )

            # Select clips and build timeline
            timeline_segments: list[TimelineSegment] = []
            clip_selections: list[ClipSelectionResult] = []
            gaps: list[dict] = []
            warnings: list[str] = []

            current_frame = 0

            for slot in slots:
                slot_results = search_results.get(slot.id, [])

                selection = self._select_clip_for_slot(
                    slot=slot,
                    search_results=slot_results,
                    file_url_map=file_url_map,
                    min_similarity=input_data.min_similarity_threshold,
                )
                clip_selections.append(selection)

                # Calculate duration in frames
                target_frames = int(slot.target_duration * self.default_fps)

                if selection.selected and selection.source_file_url:
                    # Create video clip segment
                    segment = self._create_video_segment(
                        slot=slot,
                        selection=selection,
                        start_frame=current_frame,
                        target_frames=target_frames,
                    )
                    timeline_segments.append(segment)

                    # Check duration mismatch
                    actual_duration = (
                        selection.timestamp_end - selection.timestamp_start
                        if selection.timestamp_end and selection.timestamp_start
                        else 0
                    )
                    if abs(actual_duration - slot.target_duration) > 1.0:
                        warnings.append(
                            f"Slot {slot.id}: clip duration ({actual_duration:.1f}s) "
                            f"differs from target ({slot.target_duration:.1f}s)"
                        )
                else:
                    # Handle gap based on configuration
                    gap_segment = self._handle_gap(
                        slot=slot,
                        selection=selection,
                        start_frame=current_frame,
                        target_frames=target_frames,
                        gap_handling=input_data.gap_handling,
                    )

                    if gap_segment:
                        timeline_segments.append(gap_segment)

                    gaps.append(
                        {
                            "slot_id": slot.id,
                            "beat_type": slot.beat_type,
                            "reason": selection.gap_reason or "No matching clip found",
                            "search_query": slot.search_query,
                            "handling": input_data.gap_handling,
                        }
                    )

                current_frame += target_frames

            # Build brand profile from project
            brand_profile = self._build_brand_profile(project)

            # Build audio track if provided
            audio_track = None
            if input_data.audio_url:
                audio_track = AudioTrack(
                    url=input_data.audio_url,
                    volume=0.8,
                    fade_in_frames=15,
                    fade_out_frames=30,
                )

            # Get composition dimensions
            width, height = COMPOSITION_DIMENSIONS[input_data.composition_type]

            # Build final payload
            payload = RemotionPayload(
                composition_id=input_data.composition_type,
                width=width,
                height=height,
                fps=self.default_fps,
                duration_in_frames=current_frame,
                project_id=input_data.project_id,
                visual_script_id=input_data.visual_script_id,
                brand_profile=brand_profile,
                audio_track=audio_track,
                timeline=timeline_segments,
                created_at=datetime.now(timezone.utc),
                version=1,
                gaps=gaps if gaps else None,
                warnings=warnings if warnings else None,
            )

            # Calculate stats
            stats = self._calculate_stats(
                clip_selections=clip_selections,
                gaps=gaps,
                total_frames=current_frame,
            )

            logger.info(
                f"Director Agent assembled payload for project {input_data.project_id}: "
                f"{stats['clips_selected']}/{stats['total_slots']} clips selected, "
                f"{stats['gaps_detected']} gaps"
            )

            return DirectorAgentOutput(
                payload=payload,
                stats=stats,
                success=True,
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Director Agent failed: {e}")
            raise DirectorAgentError(f"Assembly failed: {e}") from e

    async def _get_visual_script(
        self, db: AsyncSession, script_id: uuid.UUID
    ) -> VisualScript:
        """Fetch visual script by ID."""
        result = await db.execute(select(VisualScript).where(VisualScript.id == script_id))
        script = result.scalar_one_or_none()

        if not script:
            raise DirectorAgentError(f"Visual script not found: {script_id}")

        if not script.slots:
            raise DirectorAgentError(f"Visual script {script_id} has no slots")

        return script

    async def _get_project(self, db: AsyncSession, project_id: uuid.UUID) -> Project:
        """Fetch project with brand profile."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise DirectorAgentError(f"Project not found: {project_id}")

        return project

    async def _build_file_url_map(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        """Build a map of file IDs to URLs for the project."""
        result = await db.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_id)
        )
        files = result.scalars().all()
        return {f.id: f.file_url for f in files if f.file_url}

    def _select_clip_for_slot(
        self,
        slot: VisualScriptSlot,
        search_results: list[tuple[UserVideoSegment, float]],
        file_url_map: dict[uuid.UUID, str],
        min_similarity: float,
    ) -> ClipSelectionResult:
        """
        Select the best clip for a slot based on similarity and duration.

        Selection criteria:
        1. Similarity score above threshold
        2. Duration close to target (prefer slightly longer)
        3. Has valid source URL
        """
        if not search_results:
            return ClipSelectionResult(
                slot_id=slot.id,
                selected=False,
                gap_reason="No search results returned",
                alternatives=[],
            )

        # Build alternatives list
        alternatives = []
        for segment, similarity in search_results:
            source_url = (
                segment.source_file_url
                or file_url_map.get(segment.source_file_id)
            )
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
                }
            )

        # Score each candidate
        best_candidate = None
        best_score = -1

        for segment, similarity in search_results:
            if similarity < min_similarity:
                continue

            source_url = (
                segment.source_file_url
                or file_url_map.get(segment.source_file_id)
            )
            if not source_url:
                continue

            # Calculate composite score
            # Similarity is weighted heavily (70%)
            # Duration match is weighted 30%
            duration = segment.duration_seconds or 0
            target = slot.target_duration

            # Duration score: 1.0 if exact match, decreasing with difference
            # Slightly prefer longer clips (can trim) over shorter
            if duration >= target:
                duration_score = max(0, 1.0 - (duration - target) / (target * 2))
            else:
                duration_score = max(0, 1.0 - (target - duration) / target)

            composite_score = (similarity * 0.7) + (duration_score * 0.3)

            if composite_score > best_score:
                best_score = composite_score
                best_candidate = (segment, similarity, source_url)

        if not best_candidate:
            return ClipSelectionResult(
                slot_id=slot.id,
                selected=False,
                gap_reason=f"No clips above similarity threshold ({min_similarity})",
                alternatives=alternatives,
            )

        segment, similarity, source_url = best_candidate

        return ClipSelectionResult(
            slot_id=slot.id,
            selected=True,
            segment_id=segment.id,
            source_file_url=source_url,
            timestamp_start=segment.timestamp_start,
            timestamp_end=segment.timestamp_end,
            similarity_score=similarity,
            alternatives=alternatives,
        )

    def _create_video_segment(
        self,
        slot: VisualScriptSlot,
        selection: ClipSelectionResult,
        start_frame: int,
        target_frames: int,
    ) -> TimelineSegment:
        """Create a video clip timeline segment."""
        # Build text overlay if slot has overlay text
        overlay = None
        if slot.overlay_text:
            position = TextPosition.CENTER
            if slot.text_position:
                try:
                    position = TextPosition(slot.text_position.lower().replace("-", "_"))
                except ValueError:
                    position = TextPosition.CENTER

            overlay = TextOverlay(
                text=slot.overlay_text,
                position=position,
                font_size=48,
                font_weight="bold",
                color="#FFFFFF",
                background="rgba(0,0,0,0.5)",
                animation=TextAnimation.POP_IN,
            )

        # Build transitions
        transition_out = None
        if slot.transition_out:
            try:
                trans_type = TransitionType(slot.transition_out.lower().replace("-", "_"))
                transition_out = Transition(
                    type=trans_type,
                    duration_frames=10 if trans_type != TransitionType.CUT else 0,
                )
            except ValueError:
                pass

        return TimelineSegment(
            id=f"segment_{slot.id}",
            type=SegmentType.VIDEO_CLIP,
            start_frame=start_frame,
            duration_frames=target_frames,
            source=VideoClipSource(
                url=selection.source_file_url or "",
                start_time=selection.timestamp_start or 0,
                end_time=selection.timestamp_end or slot.target_duration,
            ),
            overlay=overlay,
            transition_out=transition_out,
            beat_type=slot.beat_type,
            slot_id=slot.id,
            search_query=slot.search_query,
            similarity_score=selection.similarity_score,
            alternative_clips=selection.alternatives,
        )

    def _handle_gap(
        self,
        slot: VisualScriptSlot,
        selection: ClipSelectionResult,
        start_frame: int,
        target_frames: int,
        gap_handling: str,
    ) -> TimelineSegment | None:
        """Handle a gap where no suitable clip was found."""
        if gap_handling == "skip":
            return None

        if gap_handling == "text_slide":
            # Create a text slide with the overlay text or beat type
            headline = slot.overlay_text or f"{slot.beat_type.title()} Section"
            return TimelineSegment(
                id=f"segment_{slot.id}_gap",
                type=SegmentType.TEXT_SLIDE,
                start_frame=start_frame,
                duration_frames=target_frames,
                text_content=TextSlideContent(
                    headline=headline,
                    subheadline=slot.notes,
                    background_color="#1a1a2e",
                    text_color="#FFFFFF",
                ),
                beat_type=slot.beat_type,
                slot_id=slot.id,
                search_query=slot.search_query,
                alternative_clips=selection.alternatives,
            )

        # Default: B-Roll generation prompt
        generation_prompt = self._generate_broll_prompt(slot)
        return TimelineSegment(
            id=f"segment_{slot.id}_broll",
            type=SegmentType.GENERATED_BROLL,
            start_frame=start_frame,
            duration_frames=target_frames,
            generated_source=GeneratedBRollSource(
                url=None,  # Will be populated after Veo 2 generation
                generation_prompt=generation_prompt,
                regenerate_available=True,
            ),
            overlay=TextOverlay(
                text=slot.overlay_text or "",
                position=TextPosition.CENTER,
                font_size=48,
                color="#FFFFFF",
            )
            if slot.overlay_text
            else None,
            beat_type=slot.beat_type,
            slot_id=slot.id,
            search_query=slot.search_query,
            alternative_clips=selection.alternatives,
        )

    def _generate_broll_prompt(self, slot: VisualScriptSlot) -> str:
        """Generate a B-Roll prompt based on slot requirements."""
        parts = []

        # Start with search query as base
        if slot.search_query:
            parts.append(slot.search_query)

        # Add characteristics
        if slot.characteristics:
            parts.append(f"Style: {', '.join(slot.characteristics)}")

        # Add cinematics if specified
        if slot.cinematics:
            cinematic_parts = []
            if "camera_angle" in slot.cinematics:
                cinematic_parts.append(f"camera: {slot.cinematics['camera_angle']}")
            if "lighting" in slot.cinematics:
                cinematic_parts.append(f"lighting: {slot.cinematics['lighting']}")
            if "motion_type" in slot.cinematics:
                cinematic_parts.append(f"motion: {slot.cinematics['motion_type']}")
            if cinematic_parts:
                parts.append(f"Cinematics: {', '.join(cinematic_parts)}")

        # Add beat context
        parts.append(f"For {slot.beat_type} section of video ad")

        # Add duration constraint
        parts.append(f"Duration: {slot.target_duration:.1f} seconds")

        return ". ".join(parts)

    def _build_brand_profile(self, project: Project) -> BrandProfile | None:
        """Build brand profile from project's brand profile if available."""
        if not project.brand_profile:
            return None

        bp = project.brand_profile
        return BrandProfile(
            primary_color=bp.primary_color,
            font_family=bp.font_family,
            logo_url=bp.logo_url,
        )

    def _calculate_stats(
        self,
        clip_selections: list[ClipSelectionResult],
        gaps: list[dict],
        total_frames: int,
    ) -> dict:
        """Calculate assembly statistics."""
        total_slots = len(clip_selections)
        clips_selected = sum(1 for s in clip_selections if s.selected)
        gaps_detected = len(gaps)

        # Calculate average similarity of selected clips
        similarities = [
            s.similarity_score for s in clip_selections if s.selected and s.similarity_score
        ]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0

        return {
            "total_slots": total_slots,
            "clips_selected": clips_selected,
            "gaps_detected": gaps_detected,
            "coverage_percentage": (clips_selected / total_slots * 100) if total_slots else 0,
            "average_similarity": round(avg_similarity, 3),
            "total_duration_seconds": total_frames / self.default_fps,
            "total_frames": total_frames,
        }

    async def get_clip_alternatives(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        slot_id: str,
        search_query: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get alternative clips for a slot (for the replacement UI).

        Args:
            db: Database session
            project_id: Project ID
            slot_id: Slot ID for context
            search_query: Search query to use
            limit: Maximum alternatives to return

        Returns:
            List of alternative clip options
        """
        results = await self.semantic_search.search_project_segments(
            db=db,
            project_id=project_id,
            query=search_query,
            limit=limit,
            min_similarity=0.3,  # Lower threshold to show more options
        )

        file_url_map = await self._build_file_url_map(db, project_id)

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

    async def update_segment_clip(
        self,
        payload: RemotionPayload,
        segment_id: str,
        new_segment: UserVideoSegment,
        source_url: str,
    ) -> RemotionPayload:
        """
        Update a segment in the payload with a different clip.

        Used when user selects a replacement clip from alternatives.

        Args:
            payload: Current Remotion payload
            segment_id: ID of segment to update
            new_segment: New UserVideoSegment to use
            source_url: URL to the source file

        Returns:
            Updated RemotionPayload
        """
        for i, segment in enumerate(payload.timeline):
            if segment.id == segment_id:
                # Update to video clip type with new source
                payload.timeline[i] = TimelineSegment(
                    id=segment.id,
                    type=SegmentType.VIDEO_CLIP,
                    start_frame=segment.start_frame,
                    duration_frames=segment.duration_frames,
                    source=VideoClipSource(
                        url=source_url,
                        start_time=new_segment.timestamp_start,
                        end_time=new_segment.timestamp_end,
                    ),
                    overlay=segment.overlay,
                    transition_in=segment.transition_in,
                    transition_out=segment.transition_out,
                    beat_type=segment.beat_type,
                    slot_id=segment.slot_id,
                    search_query=segment.search_query,
                    similarity_score=None,  # Will be recalculated if needed
                    alternative_clips=segment.alternative_clips,
                )

                # Increment version
                payload.version += 1
                break

        return payload
