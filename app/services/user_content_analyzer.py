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
You are an expert video content analyzer. Your job is to segment this user-uploaded video into
distinct, reusable clips for ad creation. Each segment should be a self-contained visual unit
that could be used as a clip in a video advertisement.

ANALYSIS GOALS:
1. Identify distinct visual segments based on scene changes, camera movement, or content shifts
2. Describe each segment in detail for semantic search and clip matching
3. Extract actionable tags for each segment to enable content discovery

SEGMENT IDENTIFICATION RULES:
- Minimum segment length: 1 second
- Maximum segment length: 15 seconds (break longer scenes into smaller units)
- Segment boundaries should be at natural cut points (scene changes, camera moves, etc.)
- Each segment should be describable as a single, coherent visual idea

FOR EACH SEGMENT, PROVIDE:
1. **Precise timestamps** (start and end in seconds, e.g., 0.0-3.5)
2. **Visual description**: Detailed description of what's visible (who, what, where, how)
   - Be specific enough that someone could search for this clip by description
   - Include: subjects, actions, setting, colors, lighting, camera angle
3. **Action tags**: 3-8 short tags describing the action/content (e.g., "product-demo", "hands", "close-up")
4. **Scene type**: Categorize as one of:
   - product_demo: Product being shown or demonstrated
   - testimonial: Person speaking to camera
   - b_roll: Supplementary footage (lifestyle, environment, abstract)
   - unboxing: Product unboxing/reveal
   - before_after: Comparison or transformation
   - text_slide: Text-heavy frame
   - logo_end_card: Logo or branding element
   - transition: Transition effect or filler
   - lifestyle: Product in real-world use context
   - talking_head: Person speaking (not testimonial format)
   - hands_demo: Close-up of hands demonstrating
   - screen_recording: Screen capture content
5. **Emotion**: Dominant emotion (excitement, calm, urgency, trust, curiosity, joy, neutral)
6. **Camera shot**: close-up, medium, wide, extreme-close-up, POV, over-shoulder
7. **Motion type**: static, handheld, tracking, pan, zoom, dolly
8. **Content flags**: has_text_overlay, has_face, has_product (boolean)

ALSO PROVIDE VIDEO-LEVEL SUMMARY:
- Overall theme and content type
- Production style (UGC, professional, hybrid)
- Key subjects/products visible
- Dominant mood/tone
- Total duration

Return analysis in this EXACT JSON structure:
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
      "visual_description": "Close-up of hands holding a sleek silver smartphone, tilting it to show the camera module. Soft natural lighting, white background.",
      "action_tags": ["hands", "smartphone", "product-reveal", "close-up", "tech"],
      "scene_type": "product_demo",
      "emotion": "curiosity",
      "camera_shot": "close-up",
      "motion_type": "handheld",
      "has_text_overlay": false,
      "has_face": false,
      "has_product": true
    }},
    {{
      "timestamp_start": 3.5,
      "timestamp_end": 8.0,
      "visual_description": "Young woman in her 20s smiling at camera in a modern office. Speaking enthusiastically with hand gestures. Ring light visible in eye reflection.",
      "action_tags": ["testimonial", "female", "office", "speaking", "enthusiastic"],
      "scene_type": "testimonial",
      "emotion": "excitement",
      "camera_shot": "medium",
      "motion_type": "static",
      "has_text_overlay": false,
      "has_face": true,
      "has_product": false
    }}
  ]
}}

CRITICAL INSTRUCTIONS:
- Be EXHAUSTIVE - capture EVERY distinct visual moment
- Timestamps must be precise and non-overlapping
- Descriptions should be search-friendly (avoid vague language like "something" or "stuff")
- Tags should be lowercase, hyphenated for multi-word (e.g., "product-demo")
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

    def _build_segment_text(self, segment: SegmentAnalysis) -> str:
        """
        Build rich text representation for embedding.

        Combines visual description and tags for optimal semantic search matching.

        Args:
            segment: The segment to build text for

        Returns:
            Combined text suitable for embedding
        """
        parts = [segment.visual_description]

        if segment.action_tags:
            parts.append(f"Actions: {', '.join(segment.action_tags)}")

        if segment.scene_type:
            parts.append(f"Scene type: {segment.scene_type}")

        if segment.emotion:
            parts.append(f"Emotion: {segment.emotion}")

        if segment.camera_shot:
            parts.append(f"Camera: {segment.camera_shot}")

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

            # Create segments
            created_segments = []
            for segment_data in analysis_result.segments:
                # Generate embedding for segment
                embedding = await self.generate_segment_embedding(segment_data)

                # Create segment record
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
                )
                db.add(segment)
                created_segments.append(segment)

            # Update file status to completed
            project_file.status = ProjectFile.STATUS_COMPLETED
            await db.commit()

            logger.info(
                f"Created {len(created_segments)} segments for file {project_file.id}"
            )
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
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()

        if not project:
            raise UserContentAnalyzerError(f"Project not found: {project_id}")

        # Get files to analyze
        file_query = select(ProjectFile).where(ProjectFile.project_id == project_id)

        if not force_reanalyze:
            file_query = file_query.where(
                ProjectFile.status.in_([
                    ProjectFile.STATUS_PENDING,
                    ProjectFile.STATUS_FAILED,
                ])
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
            select(UserVideoSegment).where(
                UserVideoSegment.source_file_id == project_file_id
            )
        )
        segments = result.scalars().all()

        for segment in segments:
            await db.delete(segment)

        await db.commit()
        return len(segments)
