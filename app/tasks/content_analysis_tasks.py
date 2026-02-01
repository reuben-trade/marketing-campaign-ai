"""User content analysis background tasks.

This module provides Celery tasks for automatically analyzing uploaded video files
using the Gemini-powered UserContentAnalyzer service. Tasks are triggered when
files are uploaded to auto-process content without manual intervention.
"""

import asyncio
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
    # Convert async URL to sync (remove asyncpg, psycopg will use sync mode)
    sync_url = settings.database_url.replace("+asyncpg", "").replace("+psycopg", "")

    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


def get_async_session():
    """Get an async database session for running async code in Celery tasks."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings

    settings = get_settings()
    # Ensure we have async driver
    database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return async_session_maker


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def analyze_project_file_task(self, file_id: str):
    """
    Analyze a single project file using Gemini.

    This task is triggered automatically when a file is uploaded. It:
    1. Downloads the video from Supabase storage
    2. Sends it to Gemini for segment analysis
    3. Generates embeddings for each segment
    4. Stores segments in the database
    5. Triggers subtitle processing for transcript data

    Args:
        file_id: UUID of the project_file to analyze

    Returns:
        Dict with analysis status and segment count

    Retries:
        - Max 3 retries with exponential backoff (60s, 120s, 240s, capped at 600s)
        - Retries on any exception (Gemini rate limits, network errors, etc.)
    """
    from app.models.project_file import ProjectFile
    from app.services.user_content_analyzer import UserContentAnalyzer, UserContentAnalyzerError

    logger.info(f"Starting content analysis for file: {file_id}")

    async def run_analysis():
        """Run the async analysis within an event loop."""
        async_session_maker = get_async_session()

        async with async_session_maker() as db:
            try:
                # Get the project file
                from sqlalchemy import select

                result = await db.execute(
                    select(ProjectFile).where(ProjectFile.id == UUID(file_id))
                )
                project_file = result.scalar_one_or_none()

                if not project_file:
                    logger.error(f"Project file not found: {file_id}")
                    return {"status": "error", "error": "Project file not found"}

                # Skip if already completed
                if project_file.status == ProjectFile.STATUS_COMPLETED:
                    logger.info(f"File {file_id} already analyzed, skipping")
                    return {"status": "skipped", "reason": "Already completed"}

                # Skip if already processing (avoid duplicate processing)
                if project_file.status == ProjectFile.STATUS_PROCESSING:
                    logger.info(f"File {file_id} already processing, skipping")
                    return {"status": "skipped", "reason": "Already processing"}

                # Run analysis
                analyzer = UserContentAnalyzer()
                segments = await analyzer.analyze_project_file(db, project_file)

                logger.info(
                    f"Content analysis completed for file {file_id}: "
                    f"{len(segments)} segments created"
                )

                return {
                    "status": "completed",
                    "file_id": file_id,
                    "segments_created": len(segments),
                }

            except UserContentAnalyzerError as e:
                logger.error(f"Analysis error for file {file_id}: {e}")
                # Let Celery handle retry via autoretry_for
                raise

            except Exception as e:
                logger.error(f"Unexpected error analyzing file {file_id}: {e}")
                raise

    try:
        return asyncio.run(run_analysis())

    except Exception as e:
        logger.error(
            f"Content analysis task failed for file {file_id} "
            f"(attempt {self.request.retries + 1}/{self.max_retries + 1}): {e}"
        )
        raise


@celery_app.task(bind=True, max_retries=2)
def analyze_project_task(self, project_id: str, force_reanalyze: bool = False):
    """
    Analyze all pending files in a project.

    This task can be triggered to analyze all files in a project at once,
    rather than processing files individually. Useful for batch operations.

    Args:
        project_id: UUID of the project to analyze
        force_reanalyze: If True, re-analyze completed files

    Returns:
        Dict with analysis progress summary
    """
    from app.services.user_content_analyzer import UserContentAnalyzer, UserContentAnalyzerError

    logger.info(f"Starting project analysis: {project_id} (force={force_reanalyze})")

    async def run_project_analysis():
        """Run the async project analysis."""
        async_session_maker = get_async_session()

        async with async_session_maker() as db:
            try:
                analyzer = UserContentAnalyzer()
                progress = await analyzer.analyze_project(db, UUID(project_id), force_reanalyze)

                logger.info(
                    f"Project analysis completed: {project_id} - "
                    f"{progress.completed_files}/{progress.total_files} files, "
                    f"{progress.segments_extracted} segments"
                )

                return {
                    "status": progress.status,
                    "project_id": project_id,
                    "total_files": progress.total_files,
                    "completed_files": progress.completed_files,
                    "segments_extracted": progress.segments_extracted,
                    "error": progress.error_message,
                }

            except UserContentAnalyzerError as e:
                logger.error(f"Project analysis error: {e}")
                raise

    try:
        return asyncio.run(run_project_analysis())

    except Exception as e:
        logger.error(f"Project analysis task failed: {project_id}: {e}")
        # Retry with backoff
        self.retry(exc=e, countdown=60 * (2**self.request.retries))


@celery_app.task
def analyze_pending_files_task(batch_size: int = 10):
    """
    Analyze all pending project files.

    This batch task finds all files with status 'pending' or 'failed'
    and queues individual analysis tasks for each.

    Args:
        batch_size: Maximum number of files to process in one batch

    Returns:
        Dict with queued file count
    """
    from app.models.project_file import ProjectFile

    session = get_sync_session()

    try:
        pending_files = (
            session.query(ProjectFile)
            .filter(ProjectFile.status.in_([ProjectFile.STATUS_PENDING, ProjectFile.STATUS_FAILED]))
            .limit(batch_size)
            .all()
        )

        queued = 0
        for project_file in pending_files:
            analyze_project_file_task.delay(str(project_file.id))
            queued += 1

        logger.info(f"Queued {queued} files for content analysis")

        return {
            "status": "completed",
            "queued": queued,
            "batch_size": batch_size,
        }

    except Exception as e:
        logger.error(f"Failed to queue pending files: {e}")
        return {"status": "error", "error": str(e)}

    finally:
        session.close()


@celery_app.task
def retry_failed_analysis_task():
    """
    Retry analysis for files that previously failed.

    This maintenance task finds all files with 'failed' status and
    resets them to 'pending' before queueing for analysis.

    Returns:
        Dict with retry count
    """
    from app.models.project_file import ProjectFile

    session = get_sync_session()

    try:
        failed_files = (
            session.query(ProjectFile).filter(ProjectFile.status == ProjectFile.STATUS_FAILED).all()
        )

        queued = 0
        for project_file in failed_files:
            # Reset status to pending before queueing
            project_file.status = ProjectFile.STATUS_PENDING
            analyze_project_file_task.delay(str(project_file.id))
            queued += 1

        session.commit()

        logger.info(f"Queued {queued} failed files for retry")

        return {
            "status": "completed",
            "queued": queued,
        }

    except Exception as e:
        logger.error(f"Failed to queue retry: {e}")
        session.rollback()
        return {"status": "error", "error": str(e)}

    finally:
        session.close()
