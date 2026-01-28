"""User content analysis service for analyzing uploaded videos."""

import asyncio
import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user_video_segment import UserVideoSegment
from app.schemas.user_video_segment import (
    AnalysisProgress,
    SegmentAnalysis,
    VideoAnalysisResult,
)
from app.services.embedding_service import EmbeddingService
from app.utils.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)


USER_CONTENT_ANALYSIS_PROMPT = """
You are an expert video content analyzer specializing in ad creation. Your job is to segment this
user-uploaded video into distinct, reusable clips with rich metadata for intelligent video editing.

================================================================================
ANALYSIS GOALS
================================================================================
1. Segment the video at natural cut points (scene changes, camera moves, content shifts)
2. Extract FULL TRANSCRIPT with word-level timestamps for caption generation
3. Classify each segment by beat type for ad structure matching
4. Provide quality scores for intelligent clip selection

================================================================================
SEGMENT IDENTIFICATION RULES
================================================================================
- Minimum segment length: 1 second
- Maximum segment length: 15 seconds (break longer scenes into smaller units)
- Segment boundaries should be at natural cut points
- Each segment should be describable as a single, coherent visual idea

================================================================================
FOR EACH SEGMENT, PROVIDE:
================================================================================

**BASIC INFO:**
1. Precise timestamps (start and end in seconds, e.g., 0.0-3.5)
2. Visual description: Detailed storyboard-quality description
3. Action tags: 3-8 lowercase, hyphenated tags (e.g., "product-demo", "hands")

**SCENE CLASSIFICATION:**
4. scene_type: product_demo | testimonial | b_roll | unboxing | before_after |
   text_slide | logo_end_card | transition | lifestyle | talking_head | hands_demo | screen_recording
5. beat_type: hook | problem | solution | showcase | cta | testimonial | benefit | transition
   - hook: Attention-grabbing opening moment
   - problem: Shows pain point or frustration
   - solution: Product/service as the answer
   - showcase: Product demo or feature highlight
   - cta: Call-to-action moment
   - testimonial: Social proof or endorsement
   - benefit: Value proposition or result
   - transition: Visual bridge between sections

**TRANSCRIPT (CRITICAL FOR CAPTIONS):**
6. transcript_text: Full verbatim transcript of ALL speech in this segment
7. transcript_words: Array of word-level timestamps for caption sync:
   [{{"word": "Hey", "start": 0.0, "end": 0.3}}, {{"word": "guys", "start": 0.35, "end": 0.6}}]
8. speaker_label: "speaker_1", "speaker_2", etc. for multi-speaker videos
9. has_speech: true/false - whether segment contains spoken words

**QUALITY SCORES:**
10. attention_score: 1-10 thumb-stop potential (how attention-grabbing is this?)
11. emotion_intensity: 1-10 emotional impact level
12. emotion: excitement | calm | urgency | trust | curiosity | joy | frustration | neutral

**CINEMATICS:**
13. camera_shot: close-up | medium | wide | extreme-close-up | POV | over-shoulder
14. motion_type: static | handheld | tracking | pan | zoom | dolly
15. color_grading: warm | cool | neutral | high-contrast | desaturated | vibrant
16. lighting_style: natural | studio | ring-light | golden-hour | harsh | soft | dramatic

**CONTENT FLAGS:**
17. has_text_overlay: true/false
18. has_face: true/false
19. has_product: true/false
20. power_words_detected: Array of persuasive words found in transcript
    (e.g., ["free", "guaranteed", "exclusive", "instant", "proven", "secret"])

================================================================================
VIDEO-LEVEL SUMMARY
================================================================================
- Overall theme and content type
- Production style (UGC, professional, hybrid)
- Key subjects/products visible
- Dominant mood/tone
- Total duration

================================================================================
RETURN THIS EXACT JSON STRUCTURE:
================================================================================
{{
  "video_level_summary": "2-3 sentence summary of what this video contains",
  "video_level_tags": ["tag1", "tag2", "tag3"],
  "total_duration_seconds": 30.0,
  "dominant_theme": "product showcase | testimonial | lifestyle | demo | tutorial | unboxing | behind-the-scenes",
  "production_style": "UGC | professional | hybrid | screen_recording",
  "content_type": "demo | testimonial | lifestyle | b-roll | tutorial | unboxing | mixed",
  "segments": [
    {{
      "timestamp_start": 0.0,
      "timestamp_end": 3.5,
      "visual_description": "Close-up of hands holding a sleek silver smartphone...",
      "action_tags": ["hands", "smartphone", "product-reveal", "close-up"],
      "scene_type": "product_demo",
      "beat_type": "hook",
      "emotion": "curiosity",
      "emotion_intensity": 7,
      "attention_score": 8,
      "camera_shot": "close-up",
      "motion_type": "handheld",
      "color_grading": "warm",
      "lighting_style": "natural",
      "has_text_overlay": false,
      "has_face": false,
      "has_product": true,
      "has_speech": true,
      "transcript_text": "Hey guys, check this out",
      "transcript_words": [
        {{"word": "Hey", "start": 0.1, "end": 0.3}},
        {{"word": "guys", "start": 0.35, "end": 0.55}},
        {{"word": "check", "start": 0.6, "end": 0.8}},
        {{"word": "this", "start": 0.85, "end": 1.0}},
        {{"word": "out", "start": 1.05, "end": 1.3}}
      ],
      "speaker_label": "speaker_1",
      "power_words_detected": []
    }},
    {{
      "timestamp_start": 3.5,
      "timestamp_end": 8.0,
      "visual_description": "Young woman smiling at camera in modern office...",
      "action_tags": ["testimonial", "female", "office", "speaking"],
      "scene_type": "testimonial",
      "beat_type": "testimonial",
      "emotion": "excitement",
      "emotion_intensity": 8,
      "attention_score": 7,
      "camera_shot": "medium",
      "motion_type": "static",
      "color_grading": "neutral",
      "lighting_style": "ring-light",
      "has_text_overlay": false,
      "has_face": true,
      "has_product": false,
      "has_speech": true,
      "transcript_text": "This product completely changed my life, I guarantee you'll love it",
      "transcript_words": [
        {{"word": "This", "start": 3.5, "end": 3.7}},
        {{"word": "product", "start": 3.75, "end": 4.1}},
        {{"word": "completely", "start": 4.15, "end": 4.6}},
        {{"word": "changed", "start": 4.65, "end": 4.95}},
        {{"word": "my", "start": 5.0, "end": 5.15}},
        {{"word": "life", "start": 5.2, "end": 5.5}},
        {{"word": "I", "start": 5.6, "end": 5.7}},
        {{"word": "guarantee", "start": 5.75, "end": 6.3}},
        {{"word": "you'll", "start": 6.35, "end": 6.55}},
        {{"word": "love", "start": 6.6, "end": 6.85}},
        {{"word": "it", "start": 6.9, "end": 7.1}}
      ],
      "speaker_label": "speaker_1",
      "power_words_detected": ["guarantee"]
    }}
  ]
}}

================================================================================
CRITICAL INSTRUCTIONS
================================================================================
- Be EXHAUSTIVE - capture EVERY distinct visual moment
- Timestamps must be precise and non-overlapping
- Descriptions should be search-friendly (avoid vague language)
- Tags should be lowercase, hyphenated for multi-word
- TRANSCRIBE ALL SPEECH verbatim with word-level timestamps
- Include ALL segments, even brief transitions or text cards
- Return ONLY valid JSON, no markdown formatting
"""


class UserContentAnalyzerError(Exception):
    """Exception raised when user content analysis fails."""

    pass


class UserContentAnalyzer:
    """
    Analyzes user-uploaded videos to extract timestamped segments.

    Pipeline:
    1. Fetch video from Supabase storage
    2. Send to Gemini for segment analysis
    3. Generate embeddings for each segment description
    4. Store segments in database
    """

    def __init__(self) -> None:
        """Initialize the user content analyzer."""
        settings = get_settings()
        self.gemini_client = genai.Client(api_key=settings.google_api_key)
        self.embedding_service = EmbeddingService()
        self.model_name = "gemini-2.0-flash"
        self.storage = SupabaseStorage()

    async def analyze_video(
        self,
        video_content: bytes,
        mime_type: str = "video/mp4",
    ) -> VideoAnalysisResult:
        """
        Analyze a video and extract timestamped segments.

        Args:
            video_content: Video file content as bytes
            mime_type: MIME type of the video

        Returns:
            VideoAnalysisResult with segments extracted from the video

        Raises:
            UserContentAnalyzerError: If analysis fails
        """
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_content)
            tmp_path = tmp.name

        try:
            # Upload video to Gemini
            video_file = self.gemini_client.files.upload(
                file=tmp_path, config={"mime_type": mime_type}
            )

            # Wait for processing
            while video_file.state == types.FileState.PROCESSING:
                await asyncio.sleep(2)
                video_file = self.gemini_client.files.get(name=video_file.name)

            if video_file.state == types.FileState.FAILED:
                raise UserContentAnalyzerError("Video processing failed in Gemini")

            # Generate analysis
            response = self.gemini_client.models.generate_content(
                model=self.model_name,
                contents=[video_file, USER_CONTENT_ANALYSIS_PROMPT],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                    max_output_tokens=16384,
                ),
            )

            result_text = response.text
            if not result_text:
                raise UserContentAnalyzerError("Empty response from Gemini")

            # Parse JSON response
            result = json.loads(result_text.strip())

            # Handle multi-encoded JSON
            max_decode_depth = 5
            decode_attempts = 0
            while isinstance(result, str) and decode_attempts < max_decode_depth:
                result = json.loads(result)
                decode_attempts += 1

            if not isinstance(result, dict):
                raise UserContentAnalyzerError(
                    f"Gemini response is not a JSON object. Got: {type(result).__name__}"
                )

            # Clean up uploaded file
            self.gemini_client.files.delete(name=video_file.name)

            # Parse into schema
            return self._parse_analysis_result(result)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise UserContentAnalyzerError(f"Failed to parse analysis: {e}") from e
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            raise UserContentAnalyzerError(f"Analysis failed: {e}") from e
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _parse_analysis_result(self, raw: dict[str, Any]) -> VideoAnalysisResult:
        """Parse raw Gemini response into VideoAnalysisResult schema."""
        segments = []
        for seg_data in raw.get("segments", []):
            # Parse transcript_words if present
            transcript_words = None
            raw_words = seg_data.get("transcript_words")
            if raw_words and isinstance(raw_words, list):
                transcript_words = [
                    {"word": w.get("word", ""), "start": w.get("start", 0), "end": w.get("end", 0)}
                    for w in raw_words
                    if isinstance(w, dict) and w.get("word")
                ]

            segment = SegmentAnalysis(
                timestamp_start=float(seg_data.get("timestamp_start", 0)),
                timestamp_end=float(seg_data.get("timestamp_end", 0)),
                visual_description=seg_data.get("visual_description", ""),
                action_tags=seg_data.get("action_tags", []),
                scene_type=seg_data.get("scene_type"),
                emotion=seg_data.get("emotion"),
                camera_shot=seg_data.get("camera_shot"),
                motion_type=seg_data.get("motion_type"),
                has_text_overlay=seg_data.get("has_text_overlay", False),
                has_face=seg_data.get("has_face", False),
                has_product=seg_data.get("has_product", False),
                # Transcript fields (Sprint 5 s5-t5)
                transcript_text=seg_data.get("transcript_text"),
                transcript_words=transcript_words,
                speaker_label=seg_data.get("speaker_label"),
                # V2 analysis fields (Sprint 5 s5-t7)
                beat_type=seg_data.get("beat_type"),
                attention_score=self._clamp_score(seg_data.get("attention_score")),
                emotion_intensity=self._clamp_score(seg_data.get("emotion_intensity")),
                color_grading=seg_data.get("color_grading"),
                lighting_style=seg_data.get("lighting_style"),
                has_speech=seg_data.get("has_speech", False),
                power_words_detected=seg_data.get("power_words_detected"),
            )
            # Calculate duration
            segment_duration = segment.timestamp_end - segment.timestamp_start
            if segment_duration > 0:
                segments.append(segment)

        return VideoAnalysisResult(
            video_level_summary=raw.get("video_level_summary", ""),
            video_level_tags=raw.get("video_level_tags", []),
            total_duration_seconds=float(raw.get("total_duration_seconds", 0)),
            segments=segments,
            dominant_theme=raw.get("dominant_theme"),
            production_style=raw.get("production_style"),
            content_type=raw.get("content_type"),
        )

    def _clamp_score(self, value: Any) -> int | None:
        """Clamp a score value to 1-10 range, return None if invalid."""
        if value is None:
            return None
        try:
            score = int(value)
            return max(1, min(10, score))
        except (TypeError, ValueError):
            return None

    def _build_segment_text(self, segment: SegmentAnalysis) -> str:
        """
        Build rich text representation for embedding.

        Combines visual description, transcript, and metadata for optimal semantic search.

        Args:
            segment: The segment to build text for

        Returns:
            Combined text suitable for embedding
        """
        parts = [segment.visual_description]

        # Include transcript for speech-based matching
        if segment.transcript_text:
            parts.append(f"Speech: {segment.transcript_text}")

        if segment.action_tags:
            parts.append(f"Actions: {', '.join(segment.action_tags)}")

        if segment.scene_type:
            parts.append(f"Scene type: {segment.scene_type}")

        if segment.beat_type:
            parts.append(f"Beat: {segment.beat_type}")

        if segment.emotion:
            parts.append(f"Emotion: {segment.emotion}")

        if segment.camera_shot:
            parts.append(f"Camera: {segment.camera_shot}")

        if segment.lighting_style:
            parts.append(f"Lighting: {segment.lighting_style}")

        return " | ".join(parts)

    async def generate_segment_embedding(self, segment: SegmentAnalysis) -> list[float]:
        """
        Generate embedding for a segment's description.

        Args:
            segment: The segment to embed

        Returns:
            1536-dimensional embedding vector
        """
        text = self._build_segment_text(segment)

        try:
            return await self.embedding_service.generate_embedding(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise UserContentAnalyzerError(f"Embedding generation failed: {e}") from e

    async def analyze_project_file(
        self,
        db: AsyncSession,
        project_file: ProjectFile,
    ) -> list[UserVideoSegment]:
        """
        Analyze a single project file and create segments.

        Args:
            db: Database session
            project_file: The project file to analyze

        Returns:
            List of created UserVideoSegment objects

        Raises:
            UserContentAnalyzerError: If analysis fails
        """
        logger.info(f"Analyzing project file: {project_file.id} - {project_file.filename}")

        # Update status to processing
        project_file.status = ProjectFile.STATUS_PROCESSING
        await db.commit()

        try:
            # Download video from storage
            video_content = await self.storage.download_file(project_file.storage_path)

            # Determine MIME type
            extension = project_file.filename.split(".")[-1].lower()
            mime_types = {
                "mp4": "video/mp4",
                "webm": "video/webm",
                "mov": "video/quicktime",
                "avi": "video/x-msvideo",
            }
            mime_type = mime_types.get(extension, "video/mp4")

            # Analyze video
            analysis_result = await self.analyze_video(video_content, mime_type)

            # Create segments with all enhanced fields
            total_segments = len(analysis_result.segments)
            created_segments = []

            for idx, segment_data in enumerate(analysis_result.segments):
                # Generate embedding for segment
                embedding = await self.generate_segment_embedding(segment_data)

                # Convert transcript_words to list of dicts for JSONB storage
                transcript_words_json = None
                if segment_data.transcript_words:
                    transcript_words_json = [
                        {"word": tw.word, "start": tw.start, "end": tw.end}
                        if hasattr(tw, "word")
                        else tw
                        for tw in segment_data.transcript_words
                    ]

                # Create segment record with all enhanced fields
                segment = UserVideoSegment(
                    project_id=project_file.project_id,
                    source_file_id=project_file.id,
                    source_file_name=project_file.original_filename,
                    source_file_url=project_file.file_url,
                    timestamp_start=segment_data.timestamp_start,
                    timestamp_end=segment_data.timestamp_end,
                    duration_seconds=segment_data.timestamp_end - segment_data.timestamp_start,
                    visual_description=segment_data.visual_description,
                    action_tags=segment_data.action_tags,
                    embedding=embedding,
                    # Clip ordering fields (Sprint 5 s5-t6)
                    segment_index=idx,
                    total_segments_in_source=total_segments,
                    # Transcript fields (Sprint 5 s5-t5)
                    transcript_text=segment_data.transcript_text,
                    transcript_words=transcript_words_json,
                    speaker_label=segment_data.speaker_label,
                    # V2 analysis fields (Sprint 5 s5-t7)
                    beat_type=segment_data.beat_type,
                    attention_score=segment_data.attention_score,
                    emotion_intensity=segment_data.emotion_intensity,
                    color_grading=segment_data.color_grading,
                    lighting_style=segment_data.lighting_style,
                    has_speech=segment_data.has_speech,
                    power_words_detected=segment_data.power_words_detected,
                )
                db.add(segment)
                created_segments.append(segment)

            # Flush to get IDs assigned
            await db.flush()

            # Set up doubly-linked list for clip ordering (Sprint 5 s5-t6)
            for idx, segment in enumerate(created_segments):
                if idx > 0:
                    segment.previous_segment_id = created_segments[idx - 1].id
                if idx < len(created_segments) - 1:
                    segment.next_segment_id = created_segments[idx + 1].id

            # Update file status to completed
            project_file.status = ProjectFile.STATUS_COMPLETED
            await db.commit()

            logger.info(f"Created {len(created_segments)} segments for file {project_file.id}")
            return created_segments

        except Exception as e:
            logger.error(f"Failed to analyze file {project_file.id}: {e}")
            project_file.status = ProjectFile.STATUS_FAILED
            await db.commit()
            raise UserContentAnalyzerError(f"File analysis failed: {e}") from e

    async def analyze_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        force_reanalyze: bool = False,
    ) -> AnalysisProgress:
        """
        Analyze all pending files in a project.

        Args:
            db: Database session
            project_id: The project to analyze
            force_reanalyze: If True, re-analyze already completed files

        Returns:
            AnalysisProgress with results

        Raises:
            UserContentAnalyzerError: If project not found or analysis fails
        """
        # Get project
        project_result = await db.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()

        if not project:
            raise UserContentAnalyzerError(f"Project not found: {project_id}")

        # Get files to analyze
        file_query = select(ProjectFile).where(ProjectFile.project_id == project_id)

        if not force_reanalyze:
            file_query = file_query.where(
                ProjectFile.status.in_(
                    [
                        ProjectFile.STATUS_PENDING,
                        ProjectFile.STATUS_FAILED,
                    ]
                )
            )

        file_result = await db.execute(file_query)
        files = file_result.scalars().all()

        if not files:
            # Check if there are any completed files
            completed_result = await db.execute(
                select(ProjectFile)
                .where(ProjectFile.project_id == project_id)
                .where(ProjectFile.status == ProjectFile.STATUS_COMPLETED)
            )
            completed_files = completed_result.scalars().all()

            # Count segments
            segment_result = await db.execute(
                select(UserVideoSegment).where(UserVideoSegment.project_id == project_id)
            )
            segments = segment_result.scalars().all()

            return AnalysisProgress(
                project_id=project_id,
                total_files=len(completed_files),
                completed_files=len(completed_files),
                status="completed",
                segments_extracted=len(segments),
            )

        # Update project status
        project.status = Project.STATUS_PROCESSING
        await db.commit()

        progress = AnalysisProgress(
            project_id=project_id,
            total_files=len(files),
            completed_files=0,
            status="processing",
        )

        total_segments = 0

        for file in files:
            try:
                progress.current_file = file.original_filename
                segments = await self.analyze_project_file(db, file)
                total_segments += len(segments)
                progress.completed_files += 1
                progress.segments_extracted = total_segments
            except Exception as e:
                logger.error(f"Failed to analyze file {file.id}: {e}")
                progress.error_message = f"Failed on {file.original_filename}: {str(e)}"
                # Continue with other files

        # Update final status
        if progress.completed_files == progress.total_files:
            progress.status = "completed"
            project.status = Project.STATUS_READY
        else:
            progress.status = "partial"
            project.status = Project.STATUS_READY  # Still mark as ready even if some failed

        await db.commit()

        return progress

    async def get_project_segments(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> list[UserVideoSegment]:
        """
        Get all segments for a project.

        Args:
            db: Database session
            project_id: The project ID

        Returns:
            List of UserVideoSegment objects
        """
        result = await db.execute(
            select(UserVideoSegment)
            .where(UserVideoSegment.project_id == project_id)
            .order_by(
                UserVideoSegment.source_file_name,
                UserVideoSegment.timestamp_start,
            )
        )
        return list(result.scalars().all())

    async def delete_file_segments(
        self,
        db: AsyncSession,
        project_file_id: uuid.UUID,
    ) -> int:
        """
        Delete all segments for a project file.

        Args:
            db: Database session
            project_file_id: The project file ID

        Returns:
            Number of deleted segments
        """
        result = await db.execute(
            select(UserVideoSegment).where(UserVideoSegment.source_file_id == project_file_id)
        )
        segments = result.scalars().all()

        for segment in segments:
            await db.delete(segment)

        await db.commit()
        return len(segments)
