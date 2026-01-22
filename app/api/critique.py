"""Critique API endpoints for user-uploaded ad analysis."""

import logging
import time
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.critique import CritiqueError, CritiqueResponse
from app.services.image_analyzer import ImageAnalysisError, ImageAnalyzer
from app.services.video_analyzer import VideoAnalysisError, VideoAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter()

# Supported file types
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "avi", "m4v"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
    "video/x-m4v",
}

# File size limits (in bytes)
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB


def get_media_type(filename: str, content_type: str | None) -> Literal["image", "video"] | None:
    """Determine if file is image or video based on extension and MIME type."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension in IMAGE_EXTENSIONS or content_type in IMAGE_MIME_TYPES:
        return "image"
    elif extension in VIDEO_EXTENSIONS or content_type in VIDEO_MIME_TYPES:
        return "video"

    return None


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
) -> CritiqueResponse:
    """
    Analyze a user-uploaded ad creative and provide comprehensive critique.

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
    if media_type == "image" and file_size > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image file too large. Maximum size: {MAX_IMAGE_SIZE // (1024 * 1024)}MB",
        )
    elif media_type == "video" and file_size > MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Video file too large. Maximum size: {MAX_VIDEO_SIZE // (1024 * 1024)}MB",
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
            )
            analysis = analyzer.parse_enhanced_analysis_v2(raw_analysis)
            model_used = "gpt-4o"

        processing_time = time.time() - start_time

        return CritiqueResponse(
            analysis=analysis,
            processing_time_seconds=round(processing_time, 2),
            model_used=model_used,
            media_type=media_type,
            file_size_bytes=file_size,
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


@router.get("/supported-formats")
async def get_supported_formats() -> dict:
    """Get list of supported file formats and size limits."""
    return {
        "image": {
            "extensions": sorted(IMAGE_EXTENSIONS),
            "mime_types": sorted(IMAGE_MIME_TYPES),
            "max_size_mb": MAX_IMAGE_SIZE // (1024 * 1024),
        },
        "video": {
            "extensions": sorted(VIDEO_EXTENSIONS),
            "mime_types": sorted(VIDEO_MIME_TYPES),
            "max_size_mb": MAX_VIDEO_SIZE // (1024 * 1024),
        },
    }
