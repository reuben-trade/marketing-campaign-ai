"""Projects API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models.project import Project
from app.models.user_video_segment import UserVideoSegment
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectStats,
    ProjectUpdate,
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

    # For now, return basic stats - video counts will be added when upload pipeline is implemented
    return ProjectStats(
        videos_uploaded=0,  # Will be populated when upload service is implemented
        total_size_mb=0.0,  # Will be populated when upload service is implemented
        segments_extracted=segments_count,
    )


async def _build_project_response(db: DbSession, project: Project) -> ProjectResponse:
    """Build a project response with stats."""
    stats = await _get_project_stats(db, project.id)

    # Convert inspiration_ads JSONB to list of UUIDs if present
    inspiration_ads = None
    if project.inspiration_ads:
        if isinstance(project.inspiration_ads, list):
            inspiration_ads = [UUID(str(ad_id)) for ad_id in project.inspiration_ads]
        elif isinstance(project.inspiration_ads, dict) and "ads" in project.inspiration_ads:
            inspiration_ads = [UUID(str(ad_id)) for ad_id in project.inspiration_ads["ads"]]

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

    await db.delete(db_project)
    await db.commit()
