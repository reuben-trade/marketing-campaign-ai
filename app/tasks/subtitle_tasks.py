"""Subtitle processing background tasks."""

import logging
from uuid import UUID

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_sync_session():
    """Get a synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import get_settings

    settings = get_settings()
    sync_url = settings.database_url.replace("+asyncpg", "")

    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(bind=True, max_retries=3)
def process_segment_subtitles_task(self, file_id: str):
    """
    Break down global SRT into per-segment transcript_text and speaker_label.

    This task is triggered after Gemini analysis completes to populate
    segment-level transcript data from the global SRT stored on project_file.

    The purpose is to support:
    - Semantic search (embeddings include transcript)
    - Segment filtering by speaker
    - API responses with transcript info

    Note: This does NOT create per-segment SRT. Remotion receives global SRT
    and handles filtering/offsetting on its own.

    Args:
        file_id: UUID of the project_file to process

    Returns:
        Dict with processing status and segment counts
    """
    from app.models.project_file import ProjectFile
    from app.models.user_video_segment import UserVideoSegment
    from app.utils.srt_parser import (
        get_dominant_speaker,
        get_transcript_for_range,
        parse_srt,
    )

    session = get_sync_session()

    try:
        # Load the project file
        project_file = session.query(ProjectFile).filter(ProjectFile.id == UUID(file_id)).first()

        if not project_file:
            logger.error(f"Project file not found: {file_id}")
            return {"status": "error", "error": "Project file not found"}

        if not project_file.srt_content:
            logger.info(f"No SRT content for file {file_id}, skipping subtitle processing")
            return {"status": "skipped", "reason": "No SRT content"}

        # Parse the global SRT
        cues = parse_srt(project_file.srt_content)

        if not cues:
            logger.info(f"No cues parsed from SRT for file {file_id}")
            return {"status": "skipped", "reason": "No cues in SRT"}

        logger.info(f"Parsed {len(cues)} SRT cues for file {file_id}")

        # Get all segments for this file
        segments = (
            session.query(UserVideoSegment)
            .filter(UserVideoSegment.source_file_id == UUID(file_id))
            .order_by(UserVideoSegment.timestamp_start)
            .all()
        )

        if not segments:
            logger.warning(f"No segments found for file {file_id}")
            return {"status": "skipped", "reason": "No segments found"}

        updated_count = 0

        for segment in segments:
            # Get transcript text for this segment's time range
            transcript = get_transcript_for_range(
                cues,
                segment.timestamp_start,
                segment.timestamp_end,
            )

            # Get dominant speaker for this segment
            speaker = get_dominant_speaker(
                cues,
                segment.timestamp_start,
                segment.timestamp_end,
            )

            # Update segment if we found transcript content
            if transcript:
                segment.transcript_text = transcript
                updated_count += 1

            if speaker:
                segment.speaker_label = speaker

        session.commit()

        logger.info(
            f"Updated {updated_count}/{len(segments)} segments with transcript data "
            f"for file {file_id}"
        )

        return {
            "status": "completed",
            "file_id": file_id,
            "total_cues": len(cues),
            "total_segments": len(segments),
            "segments_with_transcript": updated_count,
        }

    except Exception as e:
        logger.error(f"Failed to process subtitles for file {file_id}: {e}")
        session.rollback()

        # Retry with exponential backoff
        self.retry(exc=e, countdown=60 * (2**self.request.retries))

    finally:
        session.close()


@celery_app.task
def reprocess_all_subtitles_task():
    """
    Reprocess subtitles for all project files with SRT content.

    This task can be triggered manually to reprocess all subtitles,
    for example after updating the SRT parsing logic.

    Returns:
        Dict with processing summary
    """
    from app.models.project_file import ProjectFile

    session = get_sync_session()

    try:
        # Get all project files with SRT content
        files_with_srt = (
            session.query(ProjectFile)
            .filter(
                ProjectFile.srt_content.isnot(None),
                ProjectFile.status == ProjectFile.STATUS_COMPLETED,
            )
            .all()
        )

        queued = 0
        for project_file in files_with_srt:
            process_segment_subtitles_task.delay(str(project_file.id))
            queued += 1

        logger.info(f"Queued {queued} files for subtitle reprocessing")

        return {
            "status": "completed",
            "queued": queued,
        }

    except Exception as e:
        logger.error(f"Failed to queue subtitle reprocessing: {e}")
        return {"error": str(e)}

    finally:
        session.close()
