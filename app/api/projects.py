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
    GenerateAdRequest,
    GenerateAdResponse,
    GenerationStats,
    ProjectCreate,
    ProjectFileResponse,
    ProjectFilesListResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectStats,
    ProjectUpdate,
    ProjectUploadResponse,
    QuickCreateRequest,
    UploadFailure,
)
from app.schemas.remotion_payload import CompositionType, DirectorAgentInput
from app.schemas.user_video_segment import (
    AnalysisProgress,
    ProjectSegmentsResponse,
    SegmentSearchRequest,
    SegmentSearchResponse,
    UserVideoSegmentResponse,
    UserVideoSegmentWithSimilarity,
)
from app.schemas.visual_script import VisualScriptGenerateRequest
from app.services.content_planner import ContentPlanningAgent, ContentPlanningError
from app.services.director_agent import DirectorAgent, DirectorAgentError
from app.services.semantic_search_service import SemanticSearchService
from app.services.upload_service import (
    UploadError,
    UploadService,
    UploadValidationError,
)
from app.services.user_content_analyzer import (
    UserContentAnalyzer,
    UserContentAnalyzerError,
)
from app.utils.supabase_storage import SupabaseStorage, SupabaseStorageError

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_project_stats(db: DbSession, project_id: UUID) -> ProjectStats:
    """Calculate project statistics."""
    # Count segments
    segments_count = (
        await db.execute(select(func.count()).where(UserVideoSegment.project_id == project_id))
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


@router.post(
    "/quick-create",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Source project not found"},
    },
)
async def quick_create_project(
    db: DbSession,
    request: QuickCreateRequest,
) -> ProjectResponse:
    """
    Quick-create a project for the standalone editor.

    This endpoint:
    1. Auto-generates a project name based on timestamp
    2. Optionally copies analyzed segments from source projects
    3. Sets up inspiration ads for recipe extraction

    **Use cases:**
    - User opens /editor and wants to generate a video quickly
    - User selects existing projects as clip sources instead of uploading
    - User provides creative direction via user_prompt

    **Returns:**
    - Created project with auto-generated name
    - If source_project_ids provided, segments are copied to new project
    """
    from datetime import datetime as dt

    # Auto-generate project name
    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
    auto_name = f"Quick Project {timestamp}"

    # Convert inspiration_ad_ids to JSONB format
    inspiration_ads_json = None
    if request.inspiration_ad_ids:
        inspiration_ads_json = [str(ad_id) for ad_id in request.inspiration_ad_ids]

    # Create the project
    db_project = Project(
        name=auto_name,
        brand_profile_id=request.brand_profile_id,
        user_prompt=request.user_prompt,
        inspiration_ads=inspiration_ads_json,
        max_videos=20,  # Higher limit for quick projects with multiple sources
        max_total_size_mb=1000,  # Higher limit for combined sources
        status=Project.STATUS_DRAFT,
    )
    db.add(db_project)
    await db.flush()  # Get the project ID before copying segments

    # Copy segments from source projects if provided
    if request.source_project_ids:
        for source_project_id in request.source_project_ids:
            # Verify source project exists
            source_result = await db.execute(select(Project).where(Project.id == source_project_id))
            source_project = source_result.scalar_one_or_none()

            if not source_project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Source project {source_project_id} not found",
                )

            # Copy segments from source project to new project
            source_segments = await db.execute(
                select(UserVideoSegment).where(UserVideoSegment.project_id == source_project_id)
            )
            for segment in source_segments.scalars().all():
                # Create a copy of the segment for the new project
                new_segment = UserVideoSegment(
                    project_id=db_project.id,
                    source_file_id=segment.source_file_id,
                    source_file_name=segment.source_file_name,
                    source_file_url=segment.source_file_url,
                    timestamp_start=segment.timestamp_start,
                    timestamp_end=segment.timestamp_end,
                    duration_seconds=segment.duration_seconds,
                    visual_description=segment.visual_description,
                    action_tags=segment.action_tags,
                    thumbnail_url=segment.thumbnail_url,
                    embedding=segment.embedding,
                    # Enhanced analysis fields (V2)
                    transcript_text=segment.transcript_text,
                    transcript_words=segment.transcript_words,
                    speaker_label=segment.speaker_label,
                    previous_segment_id=None,  # Reset ordering for new project
                    next_segment_id=None,
                    segment_index=segment.segment_index,
                    section_type=segment.section_type,
                    section_label=segment.section_label,
                    attention_score=segment.attention_score,
                    emotion_intensity=segment.emotion_intensity,
                    power_words=segment.power_words,
                    detailed_breakdown=segment.detailed_breakdown,
                )
                db.add(new_segment)

    await db.commit()
    await db.refresh(db_project)

    logger.info(
        f"Quick-created project {db_project.id} "
        f"from {len(request.source_project_ids or [])} source projects"
    )

    return await _build_project_response(db, db_project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    db: DbSession,
    project_id: UUID,
) -> ProjectResponse:
    """Get a project by ID."""
    result = await db.execute(select(Project).where(Project.id == project_id))
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
    result = await db.execute(select(Project).where(Project.id == project_id))
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
    result = await db.execute(select(Project).where(Project.id == project_id))
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
    files: list[UploadFile] = File(
        ..., description="Video files to upload (max 10, max 100MB each)"
    ),
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
    result = await db.execute(select(Project).where(Project.id == project_id))
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
            UploadFailure(filename=f["filename"], error=f["error"]) for f in summary.failed_files
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
    result = await db.execute(select(Project).where(Project.id == project_id))
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
    storage = SupabaseStorage()
    try:
        await storage.delete_file(
            project_file.storage_path,
            bucket=storage.user_uploads_bucket,
        )
    except SupabaseStorageError as e:
        logger.warning(f"Failed to delete file from storage: {e}")

    # Delete associated segments
    analyzer = UserContentAnalyzer()
    await analyzer.delete_file_segments(db, file_id)

    # Delete from database
    await db.delete(project_file)
    await db.commit()


# =============================================================================
# CONTENT ANALYSIS ENDPOINTS
# =============================================================================


@router.post(
    "/{project_id}/analyze",
    response_model=AnalysisProgress,
    responses={
        404: {"description": "Project not found"},
        500: {"description": "Analysis failed"},
    },
)
async def analyze_project_files(
    db: DbSession,
    project_id: UUID,
    force_reanalyze: bool = Query(
        False,
        description="Re-analyze already completed files",
    ),
) -> AnalysisProgress:
    """
    Analyze all uploaded video files in a project.

    This endpoint:
    1. Sends each video to Gemini for segment extraction
    2. Generates embeddings for each segment
    3. Stores segments in the database for semantic search

    **Note:** Analysis can take 1-2 minutes per video file.
    """
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    try:
        analyzer = UserContentAnalyzer()
        progress = await analyzer.analyze_project(
            db,
            project_id,
            force_reanalyze=force_reanalyze,
        )
        return progress
    except UserContentAnalyzerError as e:
        logger.error(f"Analysis failed for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/{project_id}/files/{file_id}/analyze",
    response_model=list[UserVideoSegmentResponse],
    responses={
        404: {"description": "Project or file not found"},
        500: {"description": "Analysis failed"},
    },
)
async def analyze_single_file(
    db: DbSession,
    project_id: UUID,
    file_id: UUID,
) -> list[UserVideoSegmentResponse]:
    """
    Analyze a single video file in a project.

    This endpoint:
    1. Sends the video to Gemini for segment extraction
    2. Generates embeddings for each segment
    3. Stores segments in the database for semantic search

    **Note:** Analysis can take 1-2 minutes.
    """
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

    try:
        analyzer = UserContentAnalyzer()

        # Delete existing segments for this file first
        await analyzer.delete_file_segments(db, file_id)

        # Analyze the file
        segments = await analyzer.analyze_project_file(db, project_file)

        return [UserVideoSegmentResponse.model_validate(s) for s in segments]
    except UserContentAnalyzerError as e:
        logger.error(f"Analysis failed for file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{project_id}/segments",
    response_model=ProjectSegmentsResponse,
)
async def list_project_segments(
    db: DbSession,
    project_id: UUID,
) -> ProjectSegmentsResponse:
    """List all extracted segments for a project."""
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get segments
    analyzer = UserContentAnalyzer()
    segments = await analyzer.get_project_segments(db, project_id)

    return ProjectSegmentsResponse(
        project_id=project_id,
        total_segments=len(segments),
        segments=[UserVideoSegmentResponse.model_validate(s) for s in segments],
    )


@router.post(
    "/{project_id}/segments/search",
    response_model=SegmentSearchResponse,
    responses={
        404: {"description": "Project not found"},
    },
)
async def search_project_segments(
    db: DbSession,
    project_id: UUID,
    request: SegmentSearchRequest,
) -> SegmentSearchResponse:
    """
    Search for video segments within a project using semantic similarity.

    Uses vector similarity search to find segments matching the query.
    This is useful for the clip swap modal in the timeline editor.
    """
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Search segments using semantic search service
    search_service = SemanticSearchService()
    results = await search_service.search_project_segments(
        db=db,
        project_id=project_id,
        query=request.query,
        limit=request.limit,
        min_similarity=request.min_similarity,
    )

    # Convert to response format
    segments_with_similarity = [
        UserVideoSegmentWithSimilarity(
            id=segment.id,
            project_id=segment.project_id,
            source_file_id=segment.source_file_id,
            source_file_name=segment.source_file_name,
            source_file_url=segment.source_file_url,
            timestamp_start=segment.timestamp_start,
            timestamp_end=segment.timestamp_end,
            duration_seconds=segment.duration_seconds,
            visual_description=segment.visual_description,
            action_tags=segment.action_tags,
            thumbnail_url=segment.thumbnail_url,
            created_at=segment.created_at,
            similarity_score=similarity,
        )
        for segment, similarity in results
    ]

    return SegmentSearchResponse(
        project_id=project_id,
        query=request.query,
        total_results=len(segments_with_similarity),
        results=segments_with_similarity,
    )


# =============================================================================
# AD GENERATION ENDPOINT
# =============================================================================


@router.post(
    "/{project_id}/generate",
    response_model=GenerateAdResponse,
    responses={
        400: {"description": "Invalid request or validation error"},
        404: {"description": "Project or recipe not found"},
        422: {"description": "Project has no analyzed segments"},
        500: {"description": "Generation failed"},
    },
)
async def generate_ad(
    db: DbSession,
    project_id: UUID,
    request: GenerateAdRequest,
) -> GenerateAdResponse:
    """
    Generate an ad from a project using the full agentic pipeline.

    This endpoint orchestrates:
    1. **Writer Agent**: Generates a visual script with slots based on the recipe
    2. **Semantic Retrieval**: Finds the best matching user clips for each slot
    3. **Director Agent**: Selects final clips and generates Remotion payload

    **Prerequisites:**
    - Project must exist with uploaded and analyzed video files
    - Recipe must exist (extracted from an inspiration ad)

    **Returns:**
    - Generated Remotion payload preview
    - Assembly statistics (clips used, gaps found)
    - Warnings about any issues

    **Note:** Generation typically takes 10-30 seconds depending on project size.
    """
    # Step 1: Verify project exists and has segments
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check project has analyzed segments
    segment_count = (
        await db.execute(select(func.count()).where(UserVideoSegment.project_id == project_id))
    ).scalar() or 0

    if segment_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project has no analyzed video segments. Please upload and analyze videos first.",
        )

    # Step 2: Validate composition type
    try:
        composition_type = CompositionType(request.composition_type)
    except ValueError:
        valid_types = [t.value for t in CompositionType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid composition_type. Must be one of: {valid_types}",
        )

    # Validate gap handling
    valid_gap_handling = ["broll", "text_slide", "skip"]
    if request.gap_handling not in valid_gap_handling:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid gap_handling. Must be one of: {valid_gap_handling}",
        )

    # Step 3: Generate visual script using Content Planning Agent (Writer)
    logger.info(f"Starting ad generation for project {project_id}")

    try:
        content_planner = ContentPlanningAgent()
        script_request = VisualScriptGenerateRequest(
            project_id=project_id,
            recipe_id=request.recipe_id,
            user_prompt=request.user_prompt,
        )
        visual_script_response = await content_planner.generate(db, script_request)
        logger.info(
            f"Generated visual script {visual_script_response.id} "
            f"with {len(visual_script_response.slots)} slots"
        )
    except ContentPlanningError as e:
        logger.error(f"Content planning failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate visual script: {e}",
        )

    # Step 4: Assemble clips using Director Agent
    try:
        director = DirectorAgent()
        director_input = DirectorAgentInput(
            project_id=project_id,
            visual_script_id=visual_script_response.id,
            composition_type=composition_type,
            min_similarity_threshold=request.min_similarity_threshold,
            gap_handling=request.gap_handling,
            audio_url=request.audio_url,
        )
        director_output = await director.assemble(db, director_input)
        logger.info(
            f"Director assembled payload: {director_output.stats['clips_selected']}/"
            f"{director_output.stats['total_slots']} clips selected"
        )
    except DirectorAgentError as e:
        logger.error(f"Director agent failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assemble ad: {e}",
        )

    # Step 5: Build response with payload preview
    payload = director_output.payload
    timeline_summary = []
    for segment in payload.timeline[:10]:  # Limit preview to first 10 segments
        timeline_summary.append(
            {
                "id": segment.id,
                "type": segment.type.value,
                "beat_type": segment.beat_type,
                "duration_frames": segment.duration_frames,
                "duration_seconds": round(segment.duration_frames / payload.fps, 2),
                "has_overlay": segment.overlay is not None,
                "similarity_score": segment.similarity_score,
            }
        )

    payload_preview = {
        "composition_id": payload.composition_id.value,
        "width": payload.width,
        "height": payload.height,
        "fps": payload.fps,
        "duration_in_frames": payload.duration_in_frames,
        "duration_seconds": round(payload.duration_in_frames / payload.fps, 2),
        "timeline_segments": len(payload.timeline),
        "timeline_preview": timeline_summary,
        "has_audio": payload.audio_track is not None,
        "has_brand_profile": payload.brand_profile is not None,
    }

    # Update project status to indicate ad was generated
    project.status = Project.STATUS_READY
    await db.commit()

    return GenerateAdResponse(
        project_id=project_id,
        visual_script_id=visual_script_response.id,
        payload_preview=payload_preview,
        stats=GenerationStats(
            total_slots=director_output.stats["total_slots"],
            clips_selected=director_output.stats["clips_selected"],
            gaps_detected=director_output.stats["gaps_detected"],
            coverage_percentage=director_output.stats["coverage_percentage"],
            average_similarity=director_output.stats["average_similarity"],
            total_duration_seconds=director_output.stats["total_duration_seconds"],
        ),
        gaps=payload.gaps,
        warnings=payload.warnings,
        success=director_output.success,
    )
