"""API endpoints for video rendering."""

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_async_db
from app.schemas.render import (
    RenderCallbackPayload,
    RenderListResponse,
    RenderMode,
    RenderPayloadUpdate,
    RenderQueueStats,
    RenderRequest,
    RenderResponse,
    RenderStatus,
    RenderStatusResponse,
)
from app.services.remotion_renderer import RemotionRendererService

router = APIRouter(prefix="/api/render", tags=["render"])


def get_renderer_service(
    db: Annotated[AsyncSession, Depends(get_async_db)],
) -> RemotionRendererService:
    """Dependency to get renderer service instance."""
    return RemotionRendererService(db)


@router.post("", response_model=RenderResponse, status_code=status.HTTP_201_CREATED)
async def create_render(
    request: RenderRequest,
    background_tasks: BackgroundTasks,
    renderer: Annotated[RemotionRendererService, Depends(get_renderer_service)],
) -> RenderResponse:
    """
    Create a new render job.

    Creates a render job in pending status and optionally starts rendering
    in the background.
    """
    # Create the render job
    render = await renderer.create_render_job(
        project_id=request.project_id,
        payload=request.payload,
    )

    # Start rendering in background
    background_tasks.add_task(
        _render_in_background,
        renderer,
        render.id,
        request.mode,
    )

    return RenderResponse(
        id=render.id,
        project_id=render.project_id,
        composition_id=render.composition_id,
        status=RenderStatus(render.status),
        created_at=render.created_at,
        video_url=render.video_url,
        thumbnail_url=render.thumbnail_url,
        duration_seconds=render.duration_seconds,
        file_size_bytes=render.file_size_bytes,
        render_time_seconds=render.render_time_seconds,
    )


async def _render_in_background(
    renderer: RemotionRendererService,
    render_id: uuid.UUID,
    mode: RenderMode,
) -> None:
    """Background task to perform the actual rendering."""
    try:
        await renderer.start_render(render_id, mode)
    except Exception:
        # Error is already logged and status updated in the service
        pass


@router.get("/{render_id}", response_model=RenderStatusResponse)
async def get_render_status(
    render_id: uuid.UUID,
    renderer: Annotated[RemotionRendererService, Depends(get_renderer_service)],
) -> RenderStatusResponse:
    """
    Get the status of a render job.

    Returns detailed information about the render including progress,
    output URLs, and metadata.
    """
    render = await renderer.get_render(render_id)
    if not render:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Render {render_id} not found",
        )

    # Calculate progress based on status
    progress = 0.0
    if render.status == RenderStatus.RENDERING.value:
        progress = 50.0  # TODO: Get actual progress from render worker
    elif render.status == RenderStatus.COMPLETED.value:
        progress = 100.0

    return RenderStatusResponse(
        id=render.id,
        project_id=render.project_id,
        composition_id=render.composition_id,
        status=RenderStatus(render.status),
        progress=progress,
        video_url=render.video_url,
        thumbnail_url=render.thumbnail_url,
        duration_seconds=render.duration_seconds,
        file_size_bytes=render.file_size_bytes,
        render_time_seconds=render.render_time_seconds,
        created_at=render.created_at,
        started_at=None,  # TODO: Add started_at to model
        completed_at=None,  # TODO: Add completed_at to model
        error_message=None,  # TODO: Add error_message to model
    )


@router.put("/{render_id}/payload", response_model=RenderResponse)
async def update_render_payload(
    render_id: uuid.UUID,
    update: RenderPayloadUpdate,
    renderer: Annotated[RemotionRendererService, Depends(get_renderer_service)],
) -> RenderResponse:
    """
    Update the payload for a pending render job.

    Only works for renders in 'pending' status. Use this to modify
    the video composition before rendering starts.
    """
    try:
        render = await renderer.update_payload(render_id, update.payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not render:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Render {render_id} not found",
        )

    return RenderResponse(
        id=render.id,
        project_id=render.project_id,
        composition_id=render.composition_id,
        status=RenderStatus(render.status),
        created_at=render.created_at,
        video_url=render.video_url,
        thumbnail_url=render.thumbnail_url,
        duration_seconds=render.duration_seconds,
        file_size_bytes=render.file_size_bytes,
        render_time_seconds=render.render_time_seconds,
    )


@router.get("/project/{project_id}", response_model=RenderListResponse)
async def list_project_renders(
    project_id: uuid.UUID,
    renderer: Annotated[RemotionRendererService, Depends(get_renderer_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> RenderListResponse:
    """
    List all renders for a project.

    Returns paginated list of render jobs ordered by creation date (newest first).
    """
    renders, total = await renderer.get_project_renders(
        project_id=project_id,
        page=page,
        page_size=page_size,
    )

    return RenderListResponse(
        renders=[
            RenderResponse(
                id=r.id,
                project_id=r.project_id,
                composition_id=r.composition_id,
                status=RenderStatus(r.status),
                created_at=r.created_at,
                video_url=r.video_url,
                thumbnail_url=r.thumbnail_url,
                duration_seconds=r.duration_seconds,
                file_size_bytes=r.file_size_bytes,
                render_time_seconds=r.render_time_seconds,
            )
            for r in renders
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{render_id}/cancel", response_model=RenderResponse)
async def cancel_render(
    render_id: uuid.UUID,
    renderer: Annotated[RemotionRendererService, Depends(get_renderer_service)],
) -> RenderResponse:
    """
    Cancel a pending or rendering job.

    Cannot cancel completed renders.
    """
    try:
        render = await renderer.cancel_render(render_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not render:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Render {render_id} not found",
        )

    return RenderResponse(
        id=render.id,
        project_id=render.project_id,
        composition_id=render.composition_id,
        status=RenderStatus(render.status),
        created_at=render.created_at,
        video_url=render.video_url,
        thumbnail_url=render.thumbnail_url,
        duration_seconds=render.duration_seconds,
        file_size_bytes=render.file_size_bytes,
        render_time_seconds=render.render_time_seconds,
    )


@router.delete("/{render_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_render(
    render_id: uuid.UUID,
    renderer: Annotated[RemotionRendererService, Depends(get_renderer_service)],
) -> None:
    """
    Delete a render job and its output files.

    Permanently removes the render record and any associated video files
    from storage.
    """
    deleted = await renderer.delete_render(render_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Render {render_id} not found",
        )


@router.get("/stats/queue", response_model=RenderQueueStats)
async def get_queue_stats(
    renderer: Annotated[RemotionRendererService, Depends(get_renderer_service)],
) -> RenderQueueStats:
    """
    Get render queue statistics.

    Returns counts of pending, rendering, completed, and failed jobs,
    as well as average render time.
    """
    stats = await renderer.get_queue_stats()
    return RenderQueueStats(**stats)


@router.post("/callback", status_code=status.HTTP_200_OK)
async def render_callback(
    payload: RenderCallbackPayload,
    renderer: Annotated[RemotionRendererService, Depends(get_renderer_service)],
    x_render_callback_secret: Annotated[str, Header()] = "",
) -> dict:
    """
    Callback endpoint for render workers/Lambda to report status.

    Used by external render workers to update job status when
    rendering completes or fails.

    Requires X-Render-Callback-Secret header for authentication.
    """
    settings = get_settings()
    if not settings.render_callback_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Render callback secret not configured",
        )
    if x_render_callback_secret != settings.render_callback_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid callback secret",
        )

    render = await renderer.get_render(payload.render_id)
    if not render:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Render {payload.render_id} not found",
        )

    # Update render with callback data
    render.status = payload.status.value
    render.video_url = payload.video_url
    render.thumbnail_url = payload.thumbnail_url
    render.duration_seconds = payload.duration_seconds
    render.file_size_bytes = payload.file_size_bytes
    render.render_time_seconds = payload.render_time_seconds

    await renderer.db.commit()

    return {"status": "ok"}
