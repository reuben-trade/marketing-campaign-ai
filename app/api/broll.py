"""API endpoints for B-Roll video generation using Veo 2."""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, get_db
from app.schemas.veo_request import (
    PromptEnhancementRequest,
    PromptEnhancementResponse,
    VeoGenerateRequest,
    VeoGenerationListResponse,
    VeoGenerationResponse,
    VeoGenerationStatus,
    VeoGenerationStatusResponse,
    VeoRegenerateRequest,
    VeoSelectClipRequest,
    VeoSelectClipResponse,
)
from app.services.veo_generator import VeoGeneratorService

router = APIRouter(prefix="/api/broll", tags=["B-Roll Generation"])


def get_veo_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VeoGeneratorService:
    """Dependency to get Veo generator service instance."""
    return VeoGeneratorService(db)


@router.post("/generate", response_model=VeoGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_broll(
    request: VeoGenerateRequest,
    background_tasks: BackgroundTasks,
    veo_service: Annotated[VeoGeneratorService, Depends(get_veo_service)],
) -> VeoGenerationResponse:
    """
    Generate B-Roll video clip(s) using Veo 2.

    Creates a generation job and starts the video generation process in the background.
    Poll GET /api/broll/{generation_id} to check status and retrieve results.

    The generation process typically takes 15-30 seconds per clip variant.
    """
    # Create the generation job
    try:
        response = await veo_service.generate_broll(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Start generation in background with fresh DB session
    background_tasks.add_task(
        _generate_in_background,
        response.id,
    )

    return response


async def _generate_in_background(
    generation_id: uuid.UUID,
) -> None:
    """Background task to perform the actual video generation.

    Creates a fresh database session to avoid issues with the request session
    being closed after the response is sent.
    """
    async with async_session_maker() as db:
        try:
            veo_service = VeoGeneratorService(db)
            await veo_service.start_generation(generation_id)
            await db.commit()
        except Exception:
            await db.rollback()
            # Error is already logged and status updated in the service


@router.post(
    "/regenerate", response_model=VeoGenerationResponse, status_code=status.HTTP_201_CREATED
)
async def regenerate_broll(
    request: VeoRegenerateRequest,
    background_tasks: BackgroundTasks,
    veo_service: Annotated[VeoGeneratorService, Depends(get_veo_service)],
) -> VeoGenerationResponse:
    """
    Regenerate B-Roll based on a previous generation.

    Creates a new generation job using the original parameters, with optional overrides.
    Use this to:
    - Generate new variants with the same prompt
    - Try a modified prompt while keeping other parameters
    - Change the style or duration

    Poll GET /api/broll/{generation_id} to check status and retrieve results.
    """
    try:
        response = await veo_service.regenerate_broll(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Start generation in background with fresh DB session
    background_tasks.add_task(
        _generate_in_background,
        response.id,
    )

    return response


@router.get("/{generation_id}", response_model=VeoGenerationStatusResponse)
async def get_generation_status(
    generation_id: uuid.UUID,
    veo_service: Annotated[VeoGeneratorService, Depends(get_veo_service)],
) -> VeoGenerationStatusResponse:
    """
    Get the status of a B-Roll generation job.

    Returns detailed information including:
    - Current status (pending, processing, completed, failed)
    - Progress percentage (approximate)
    - Generated clip variants when completed
    - Error message if failed
    """
    generation = await veo_service.get_generation(generation_id)
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation {generation_id} not found",
        )

    # Calculate approximate progress
    progress = 0.0
    estimated_remaining = None

    if generation.status == VeoGenerationStatus.PENDING:
        progress = 0.0
        estimated_remaining = 30.0  # Rough estimate
    elif generation.status == VeoGenerationStatus.PROCESSING:
        progress = 50.0
        estimated_remaining = 15.0  # Rough estimate
    elif generation.status == VeoGenerationStatus.COMPLETED:
        progress = 100.0
    elif generation.status == VeoGenerationStatus.FAILED:
        progress = 0.0

    return VeoGenerationStatusResponse(
        id=generation.id,
        status=generation.status,
        progress=progress,
        clips=generation.clips,
        error_message=generation.error_message,
        estimated_time_remaining_seconds=estimated_remaining,
    )


@router.get("", response_model=VeoGenerationListResponse)
async def list_generations(
    veo_service: Annotated[VeoGeneratorService, Depends(get_veo_service)],
    project_id: uuid.UUID | None = Query(default=None, description="Filter by project ID"),
    status: VeoGenerationStatus | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> VeoGenerationListResponse:
    """
    List B-Roll generation jobs.

    Returns a paginated list of generation jobs with optional filtering
    by project ID and/or status.
    """
    generations, total = await veo_service.list_generations(
        project_id=project_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    return VeoGenerationListResponse(
        generations=generations,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation(
    generation_id: uuid.UUID,
    veo_service: Annotated[VeoGeneratorService, Depends(get_veo_service)],
) -> None:
    """
    Delete a generation job and its associated clips.

    Removes the generation record from the database and deletes
    any generated video files from storage.
    """
    deleted = await veo_service.delete_generation(generation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation {generation_id} not found",
        )


@router.post("/enhance-prompt", response_model=PromptEnhancementResponse)
async def enhance_prompt(
    request: PromptEnhancementRequest,
    veo_service: Annotated[VeoGeneratorService, Depends(get_veo_service)],
) -> PromptEnhancementResponse:
    """
    Enhance a B-Roll prompt using AI.

    Takes a basic prompt description and returns enhanced versions
    that are more likely to produce better video results.

    Useful for users who aren't sure how to describe what they want
    or want suggestions for improving their prompts.
    """
    return await veo_service.enhance_prompt(request)


@router.post("/{generation_id}/select", response_model=VeoSelectClipResponse)
async def select_clip(
    generation_id: uuid.UUID,
    request: VeoSelectClipRequest,
    veo_service: Annotated[VeoGeneratorService, Depends(get_veo_service)],
) -> VeoSelectClipResponse:
    """
    Select a generated clip for use in the timeline.

    Copies the selected clip to permanent project storage and returns
    a stable URL that can be used in the Remotion payload.

    This should be called when the user chooses which variant to use
    for their video ad.
    """
    # Validate generation_id matches
    if request.generation_id != generation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generation ID in request body does not match URL",
        )

    # Get generation to find project_id
    generation = await veo_service.get_generation(generation_id)
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation {generation_id} not found",
        )

    if not generation.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot select clip: generation is not associated with a project",
        )

    try:
        clip, storage_url = await veo_service.select_clip(
            generation_id=generation_id,
            clip_id=request.clip_id,
            project_id=generation.project_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return VeoSelectClipResponse(
        clip=clip,
        storage_url=storage_url,
    )
