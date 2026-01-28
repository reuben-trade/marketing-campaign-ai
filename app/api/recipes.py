"""Recipe API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.recipe import (
    BeatDefinition,
    RecipeExtractRequest,
    RecipeExtractResponse,
    RecipeListResponse,
    RecipeResponse,
    ReferenceAdFetchRequest,
    ReferenceAdResponse,
)
from app.services.recipe_extractor import RecipeExtractionError, RecipeExtractor
from app.services.reference_ad_service import ReferenceAdError, ReferenceAdService

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=RecipeListResponse)
async def list_recipes(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    style: Annotated[str | None, Query(description="Filter by style: ugc, polished, etc.")] = None,
    pacing: Annotated[
        str | None, Query(description="Filter by pacing: fast, medium, slow, dynamic")
    ] = None,
    min_score: Annotated[
        float | None, Query(ge=0, le=1, description="Minimum composite score (0-1)")
    ] = None,
) -> RecipeListResponse:
    """
    List available recipes with optional filtering.

    Returns recipes sorted by composite score (highest first).
    """
    extractor = RecipeExtractor()
    recipes, total = await extractor.list_recipes(
        db,
        limit=limit,
        offset=offset,
        style=style,
        pacing=pacing,
        min_score=min_score,
    )

    return RecipeListResponse(
        recipes=[
            RecipeResponse(
                id=r.id,
                source_ad_id=r.source_ad_id,
                name=r.name,
                total_duration_seconds=r.total_duration_seconds,
                structure=[BeatDefinition(**b) for b in r.structure],
                pacing=r.pacing,
                style=r.style,
                composite_score=r.composite_score,
                created_at=r.created_at,
            )
            for r in recipes
        ],
        total=total,
    )


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecipeResponse:
    """Get recipe details by ID."""
    extractor = RecipeExtractor()
    recipe = await extractor.get_recipe(db, recipe_id)

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeResponse(
        id=recipe.id,
        source_ad_id=recipe.source_ad_id,
        name=recipe.name,
        total_duration_seconds=recipe.total_duration_seconds,
        structure=[BeatDefinition(**b) for b in recipe.structure],
        pacing=recipe.pacing,
        style=recipe.style,
        composite_score=recipe.composite_score,
        created_at=recipe.created_at,
    )


@router.post("/extract", response_model=RecipeExtractResponse)
async def extract_recipe(
    request: RecipeExtractRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecipeExtractResponse:
    """
    Extract a structural recipe from an analyzed ad.

    The ad must have been analyzed (video_intelligence or elements populated).
    Returns the created recipe along with extraction notes.
    """
    extractor = RecipeExtractor()
    try:
        return await extractor.extract_from_ad(
            db,
            ad_id=request.ad_id,
            custom_name=request.name,
        )
    except RecipeExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a recipe by ID."""
    extractor = RecipeExtractor()
    deleted = await extractor.delete_recipe(db, recipe_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Recipe not found")


# Maximum file size: 500MB
MAX_REFERENCE_FILE_SIZE = 500 * 1024 * 1024
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}


@router.post("/upload-reference", response_model=ReferenceAdResponse)
async def upload_reference_ad(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="Video file to upload"),
    name: Annotated[str | None, Form(description="Optional custom name")] = None,
) -> ReferenceAdResponse:
    """
    Upload a reference ad video for analysis and recipe extraction.

    This endpoint:
    1. Uploads the video to storage
    2. Analyzes it with Gemini to extract structure
    3. Creates an ad record
    4. Extracts a recipe from the analysis

    Processing takes 2-3 minutes depending on video length.
    """
    # Validate file type
    if file.content_type and file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_VIDEO_TYPES)}",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_REFERENCE_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_REFERENCE_FILE_SIZE // 1024 // 1024}MB",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    service = ReferenceAdService()
    try:
        return await service.upload_reference_ad(
            db=db,
            file_content=content,
            filename=file.filename or "upload.mp4",
            custom_name=name,
        )
    except ReferenceAdError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/fetch-url", response_model=ReferenceAdResponse)
async def fetch_reference_ad_from_url(
    request: ReferenceAdFetchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReferenceAdResponse:
    """
    Fetch a reference ad from a URL for analysis and recipe extraction.

    Supported platforms:
    - Direct video URLs (MP4, WebM, MOV)
    - Meta Ad Library
    - TikTok Creative Center
    - YouTube (requires yt-dlp)

    Processing takes 2-3 minutes depending on video length and download speed.
    """
    service = ReferenceAdService()
    try:
        return await service.fetch_from_url(
            db=db,
            url=request.url,
            custom_name=request.name,
        )
    except ReferenceAdError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
