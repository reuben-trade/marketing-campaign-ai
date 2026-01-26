"""Projects API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user_video_segment import UserVideoSegment
from app.schemas.project import (
    ProjectCreate,
    ProjectFileResponse,
    ProjectFilesListResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectStats,
    ProjectUpdate,
    ProjectUploadResponse,
    UploadFailure,
)
from app.services.upload_service import (
    UploadError,
    UploadService,
    UploadValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_project_stats(db: DbSession, project_id: UUID) -> ProjectStats:
    """Calculate project statistics."""
    # Count segments
    segments_count = (
        await db.execute(
            select(func.count()).where(UserVideoSegment.project_id == project_id)
        )
    ).scalar() or 0

    # Get file stats
    file_stats = await db.execute(
        select(
            func.count(ProjectFile.id),
            func.coalesce(func.sum(ProjectFile.file_size_bytes), 0),
        ).where(ProjectFile.project_id == project_id)
    )
    row = file_stats.one()
    videos_uploaded = int(row[0])
    total_size_bytes = int(row[1])
    total_size_mb = total_size_bytes / (1024 * 1024) if total_size_bytes > 0 else 0.0

    return ProjectStats(
        videos_uploaded=videos_uploaded,
        total_size_mb=round(total_size_mb, 2),
        segments_extracted=segments_count,
    )


async def _build_project_response(db: DbSession, project: Project) -> ProjectResponse:
    """Build a project response with stats."""
    stats = await _get_project_stats(db, project.id)

    # Convert inspiration_ads JSONB (stored as list of UUID strings) to list of UUIDs
    inspiration_ads = None
    if project.inspiration_ads and isinstance(project.inspiration_ads, list):
        inspiration_ads = [UUID(str(ad_id)) for ad_id in project.inspiration_ads]

    return ProjectResponse(
        id=project.id,
        name=project.name,
        brand_profile_id=project.brand_profile_id,
        status=project.status,
        inspiration_ads=inspiration_ads,
        user_prompt=project.user_prompt,
        max_videos=project.max_videos,
        max_total_size_mb=project.max_total_size_mb,
        created_at=project.created_at,
        updated_at=project.updated_at,
        stats=stats,
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
) -> ProjectListResponse:
    """List all projects with pagination."""
    query = select(Project)

    if status_filter:
        if status_filter not in Project.VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(Project.VALID_STATUSES)}",
            )
        query = query.where(Project.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    projects = result.scalars().all()

    items = []
    for project in projects:
        project_response = await _build_project_response(db, project)
        items.append(project_response)

    return ProjectListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    db: DbSession,
    project: ProjectCreate,
) -> ProjectResponse:
    """Create a new project."""
    # Convert inspiration_ads list to JSONB format
    inspiration_ads_json = None
    if project.inspiration_ads:
        inspiration_ads_json = [str(ad_id) for ad_id in project.inspiration_ads]

    db_project = Project(
        name=project.name,
        brand_profile_id=project.brand_profile_id,
        user_prompt=project.user_prompt,
        inspiration_ads=inspiration_ads_json,
        max_videos=project.max_videos,
        max_total_size_mb=project.max_total_size_mb,
        status=Project.STATUS_DRAFT,
    )
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)

    return await _build_project_response(db, db_project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    db: DbSession,
    project_id: UUID,
) -> ProjectResponse:
    """Get a project by ID."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return await _build_project_response(db, project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    db: DbSession,
    project_id: UUID,
    project_update: ProjectUpdate,
) -> ProjectResponse:
    """Update a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    db_project = result.scalar_one_or_none()

    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    update_data = project_update.model_dump(exclude_unset=True)

    # Validate status if provided
    if "status" in update_data and update_data["status"] not in Project.VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(Project.VALID_STATUSES)}",
        )

    # Convert inspiration_ads to JSONB format if provided
    if "inspiration_ads" in update_data and update_data["inspiration_ads"] is not None:
        update_data["inspiration_ads"] = [str(ad_id) for ad_id in update_data["inspiration_ads"]]

    for field, value in update_data.items():
        setattr(db_project, field, value)

    await db.commit()
    await db.refresh(db_project)

    return await _build_project_response(db, db_project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    db: DbSession,
    project_id: UUID,
) -> None:
    """Delete a project and all its associated data."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    db_project = result.scalar_one_or_none()

    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Delete files from storage
    upload_service = UploadService(db)
    try:
        await upload_service.delete_project_files(project_id)
    except Exception as e:
        logger.warning(f"Failed to delete project files from storage: {e}")

    await db.delete(db_project)
    await db.commit()


@router.post(
    "/{project_id}/upload",
    response_model=ProjectUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid request or validation error"},
        404: {"description": "Project not found"},
        413: {"description": "File(s) too large or project size limit exceeded"},
    },
)
async def upload_project_files(
    db: DbSession,
    project_id: UUID,
    files: list[UploadFile] = File(..., description="Video files to upload (max 10, max 100MB each)"),
) -> ProjectUploadResponse:
    """
    Upload video files to a project.

    **Constraints:**
    - Maximum 10 videos per project (configurable per project)
    - Maximum 500MB total per project (configurable per project)
    - Maximum 100MB per individual file
    - Supported formats: mp4, mov, webm, avi, m4v, mkv

    **Returns:**
    - List of uploaded files with their URLs and metadata
    - Any files that failed to upload
    """
    # Get project
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Upload files
    upload_service = UploadService(db)

    try:
        summary = await upload_service.upload_files(project, files)
    except UploadValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except UploadError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    await db.commit()

    return ProjectUploadResponse(
        project_id=summary.project_id,
        uploaded_files=[
            ProjectFileResponse(
                file_id=f.file_id,
                filename=f.filename,
                original_filename=f.original_filename,
                file_size_bytes=f.file_size_bytes,
                file_url=f.file_url,
                status=f.status,
            )
            for f in summary.uploaded_files
        ],
        total_files=summary.total_files,
        total_size_bytes=summary.total_size_bytes,
        total_size_mb=round(summary.total_size_bytes / (1024 * 1024), 2),
        failed_files=[
            UploadFailure(filename=f["filename"], error=f["error"])
            for f in summary.failed_files
        ],
    )


@router.get(
    "/{project_id}/files",
    response_model=ProjectFilesListResponse,
)
async def list_project_files(
    db: DbSession,
    project_id: UUID,
) -> ProjectFilesListResponse:
    """List all uploaded files for a project."""
    # Verify project exists
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get files
    files_result = await db.execute(
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.created_at.desc())
    )
    files = files_result.scalars().all()

    total_size_bytes = sum(f.file_size_bytes for f in files)

    return ProjectFilesListResponse(
        project_id=project_id,
        files=[
            ProjectFileResponse(
                file_id=f.id,
                filename=f.filename,
                original_filename=f.original_filename,
                file_size_bytes=f.file_size_bytes,
                file_url=f.file_url,
                status=f.status,
            )
            for f in files
        ],
        total=len(files),
        total_size_bytes=total_size_bytes,
        total_size_mb=round(total_size_bytes / (1024 * 1024), 2) if total_size_bytes > 0 else 0.0,
    )


@router.delete(
    "/{project_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project_file(
    db: DbSession,
    project_id: UUID,
    file_id: UUID,
) -> None:
    """Delete a specific file from a project."""
    # Get file
    result = await db.execute(
        select(ProjectFile).where(
            ProjectFile.id == file_id,
            ProjectFile.project_id == project_id,
        )
    )
    project_file = result.scalar_one_or_none()

    if not project_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Delete from storage
    from app.utils.supabase_storage import SupabaseStorage, SupabaseStorageError

    storage = SupabaseStorage()
    try:
        await storage.delete_file(
            project_file.storage_path,
            bucket=storage.user_uploads_bucket,
        )
    except SupabaseStorageError as e:
        logger.warning(f"Failed to delete file from storage: {e}")

    # Delete from database
    await db.delete(project_file)
    await db.commit()
