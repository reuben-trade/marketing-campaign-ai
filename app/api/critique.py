"""Critique API endpoints for user-uploaded ad analysis."""

import logging
import time
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.critique import Critique
from app.schemas.critique import (
    CritiqueError,
    CritiqueListItem,
    CritiqueListResponse,
    CritiqueResponse,
)
from app.services.image_analyzer import ImageAnalysisError, ImageAnalyzer
from app.services.video_analyzer import VideoAnalysisError, VideoAnalyzer
from app.utils.media_types import (
    IMAGE_EXTENSIONS,
    IMAGE_MIME_TYPES,
    MAX_IMAGE_SIZE_BYTES,
    MAX_VIDEO_SIZE_BYTES,
    VIDEO_EXTENSIONS,
    VIDEO_MIME_TYPES,
    get_media_type,
)
from app.utils.supabase_storage import SupabaseStorage, SupabaseStorageError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/upload",
    response_model=CritiqueResponse,
    responses={
        400: {"model": CritiqueError, "description": "Invalid file or request"},
        413: {"model": CritiqueError, "description": "File too large"},
        415: {"model": CritiqueError, "description": "Unsupported media type"},
        500: {"model": CritiqueError, "description": "Analysis failed"},
    },
)
async def critique_uploaded_ad(
    file: UploadFile = File(..., description="Image or video file to analyze"),
    brand_name: str | None = Form(None, description="Brand/company name for context"),
    industry: str | None = Form(None, description="Industry for context"),
    target_audience: str | None = Form(None, description="Target audience description"),
    platform_cta: str | None = Form(
        None,
        description="Platform CTA button text (e.g., 'Learn More', 'Shop Now'). "
        "This is the off-screen button that appears on the ad platform.",
    ),
    db: AsyncSession = Depends(get_db),
) -> CritiqueResponse:
    """
    Analyze a user-uploaded ad creative and provide comprehensive critique.

    Results are automatically persisted to the database for future access.

    **Supported formats:**
    - Images: jpg, jpeg, png, webp, gif (max 20MB)
    - Videos: mp4, mov, webm, avi, m4v (max 100MB)

    **Returns:**
    - Full EnhancedAdAnalysisV2 with Creative DNA
    - Timestamped narrative beats (video only)
    - Actionable critique with strengths, weaknesses, and remake suggestions
    - Engagement predictions and platform optimization recommendations

    **Context parameters:**
    - brand_name: Helps the AI understand branding context
    - industry: Helps benchmark against industry standards
    - target_audience: Helps evaluate audience fit
    - platform_cta: The CTA button text on the ad platform (not visible in creative)
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    # Determine media type
    media_type = get_media_type(file.filename, file.content_type)
    if not media_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Supported: {', '.join(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)}",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if media_type == "image" and file_size > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image file too large. Maximum size: {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB",
        )
    elif media_type == "video" and file_size > MAX_VIDEO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Video file too large. Maximum size: {MAX_VIDEO_SIZE_BYTES // (1024 * 1024)}MB",
        )

    # Validate file is not empty
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    start_time = time.time()

    try:
        if media_type == "video":
            # Use VideoAnalyzer for video files
            analyzer = VideoAnalyzer()
            raw_analysis = await analyzer.analyze_video_v2(
                video_content=content,
                competitor_name="User Upload",
                brand_name=brand_name,
                industry=industry,
                target_audience=target_audience,
                platform_cta=platform_cta,
            )
            analysis = analyzer.parse_enhanced_analysis_v2(raw_analysis)
            model_used = "gemini-2.0-flash"
        else:
            # Use ImageAnalyzer for image files
            analyzer = ImageAnalyzer()
            raw_analysis = await analyzer.analyze_image_v2(
                image_content=content,
                competitor_name="User Upload",
                brand_name=brand_name,
                industry=industry,
                target_audience=target_audience,
                platform_cta=platform_cta,
            )
            analysis = analyzer.parse_enhanced_analysis_v2(raw_analysis)
            model_used = "gpt-4o"

        processing_time = time.time() - start_time

        # Extract scores for denormalized storage
        critique_data = analysis.critique
        thumb_stop = (
            analysis.engagement_predictors.thumb_stop.thumb_stop_score
            if analysis.engagement_predictors and analysis.engagement_predictors.thumb_stop
            else None
        )

        # Upload file to Supabase storage
        storage = SupabaseStorage()
        file_storage_path = None
        file_url = None

        critique_id = uuid.uuid4()
        try:
            file_storage_path = await storage.upload_critique_file(
                critique_id=critique_id,
                content=content,
                filename=file.filename,
                media_type=media_type,
            )
            file_url = storage.get_public_url(
                file_storage_path, bucket=storage.critique_files_bucket
            )
        except SupabaseStorageError as e:
            logger.warning(f"Failed to upload file to storage: {e}. Continuing without file URL.")

        # Persist to database
        critique_record = Critique(
            id=critique_id,
            file_name=file.filename,
            file_size_bytes=file_size,
            media_type=media_type,
            file_storage_path=file_storage_path,
            file_url=file_url,
            brand_name=brand_name,
            industry=industry,
            target_audience=target_audience,
            platform_cta=platform_cta,
            analysis=analysis.model_dump(),
            overall_grade=critique_data.overall_grade if critique_data else None,
            hook_score=analysis.hook_score,
            pacing_score=analysis.overall_pacing_score,
            thumb_stop_score=thumb_stop,
            analysis_confidence=analysis.analysis_confidence,
            model_used=model_used,
            processing_time_seconds=round(processing_time, 2),
        )
        db.add(critique_record)
        await db.flush()

        return CritiqueResponse(
            id=critique_record.id,
            analysis=analysis,
            processing_time_seconds=round(processing_time, 2),
            model_used=model_used,
            media_type=media_type,
            file_size_bytes=file_size,
            file_name=file.filename,
            file_url=file_url,
            created_at=critique_record.created_at,
        )

    except VideoAnalysisError as e:
        logger.error(f"Video analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video analysis failed: {str(e)}",
        )
    except ImageAnalysisError as e:
        logger.error(f"Image analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image analysis failed: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error during critique: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.get(
    "",
    response_model=CritiqueListResponse,
)
async def list_critiques(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    media_type: str | None = Query(None, description="Filter by media type: 'image' or 'video'"),
    db: AsyncSession = Depends(get_db),
) -> CritiqueListResponse:
    """List all saved critiques, ordered by most recent first."""
    # Build query
    query = select(Critique)
    count_query = select(func.count(Critique.id))

    if media_type:
        query = query.where(Critique.media_type == media_type)
        count_query = count_query.where(Critique.media_type == media_type)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(Critique.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    critiques = result.scalars().all()

    return CritiqueListResponse(
        critiques=[
            CritiqueListItem(
                id=c.id,
                file_name=c.file_name,
                file_size_bytes=c.file_size_bytes,
                media_type=c.media_type,
                file_url=c.file_url,
                brand_name=c.brand_name,
                industry=c.industry,
                overall_grade=c.overall_grade,
                hook_score=c.hook_score,
                pacing_score=c.pacing_score,
                thumb_stop_score=c.thumb_stop_score,
                model_used=c.model_used,
                processing_time_seconds=float(c.processing_time_seconds)
                if c.processing_time_seconds
                else None,
                created_at=c.created_at,
            )
            for c in critiques
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/supported-formats")
async def get_supported_formats() -> dict:
    """Get list of supported file formats and size limits."""
    return {
        "image": {
            "extensions": sorted(IMAGE_EXTENSIONS),
            "mime_types": sorted(IMAGE_MIME_TYPES),
            "max_size_mb": MAX_IMAGE_SIZE_BYTES // (1024 * 1024),
        },
        "video": {
            "extensions": sorted(VIDEO_EXTENSIONS),
            "mime_types": sorted(VIDEO_MIME_TYPES),
            "max_size_mb": MAX_VIDEO_SIZE_BYTES // (1024 * 1024),
        },
    }


@router.get(
    "/{critique_id}",
    response_model=CritiqueResponse,
    responses={404: {"model": CritiqueError, "description": "Critique not found"}},
)
async def get_critique(
    critique_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CritiqueResponse:
    """Get a specific saved critique with full analysis data."""
    result = await db.execute(select(Critique).where(Critique.id == critique_id))
    critique = result.scalar_one_or_none()

    if not critique:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Critique {critique_id} not found",
        )

    from app.schemas.ad_analysis import EnhancedAdAnalysisV2

    return CritiqueResponse(
        id=critique.id,
        analysis=EnhancedAdAnalysisV2(**critique.analysis),
        processing_time_seconds=float(critique.processing_time_seconds)
        if critique.processing_time_seconds
        else 0,
        model_used=critique.model_used or "unknown",
        media_type=critique.media_type,
        file_size_bytes=critique.file_size_bytes,
        file_name=critique.file_name,
        file_url=critique.file_url,
        created_at=critique.created_at,
    )


@router.delete(
    "/{critique_id}",
    responses={404: {"model": CritiqueError, "description": "Critique not found"}},
)
async def delete_critique(
    critique_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a saved critique and its associated file from storage."""
    result = await db.execute(select(Critique).where(Critique.id == critique_id))
    critique = result.scalar_one_or_none()

    if not critique:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Critique {critique_id} not found",
        )

    # Delete file from storage if it exists
    if critique.file_storage_path:
        try:
            storage = SupabaseStorage()
            await storage.delete_file(
                critique.file_storage_path, bucket=storage.critique_files_bucket
            )
        except SupabaseStorageError as e:
            logger.warning(
                f"Failed to delete file from storage: {e}. Continuing with critique deletion."
            )

    await db.delete(critique)
    return {"message": "Critique deleted successfully", "id": str(critique_id)}
