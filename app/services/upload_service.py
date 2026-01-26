"""Upload service for handling project file uploads."""

import logging
import uuid
from dataclasses import dataclass, field

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_file import ProjectFile
from app.utils.media_types import (
    MAX_VIDEO_SIZE_BYTES,
    VIDEO_EXTENSIONS,
    get_video_content_type,
    is_video_file,
)
from app.utils.supabase_storage import SupabaseStorage, SupabaseStorageError

logger = logging.getLogger(__name__)

MB_TO_BYTES = 1024 * 1024


class UploadError(Exception):
    """Exception raised for upload errors."""

    pass


class UploadValidationError(UploadError):
    """Exception raised for upload validation errors."""

    pass


@dataclass
class ValidatedFile:
    """A file that has been validated and its content cached."""

    file: UploadFile
    content: bytes
    size: int


@dataclass
class UploadResult:
    """Result of a single file upload."""

    file_id: uuid.UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    storage_path: str
    file_url: str
    status: str


@dataclass
class UploadSummary:
    """Summary of upload operation."""

    project_id: uuid.UUID
    uploaded_files: list[UploadResult] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    failed_files: list[dict] = field(default_factory=list)


class UploadService:
    """Service for handling project file uploads."""

    def __init__(self, db: AsyncSession):
        """Initialize upload service."""
        self.db = db
        self.storage = SupabaseStorage()

    async def get_project_upload_stats(
        self, project_id: uuid.UUID
    ) -> tuple[int, int]:
        """
        Get current upload statistics for a project.

        Returns:
            Tuple of (file_count, total_size_bytes)
        """
        result = await self.db.execute(
            select(
                func.count(ProjectFile.id),
                func.coalesce(func.sum(ProjectFile.file_size_bytes), 0),
            ).where(ProjectFile.project_id == project_id)
        )
        row = result.one()
        return int(row[0]), int(row[1])

    async def validate_and_read_files(
        self,
        project: Project,
        files: list[UploadFile],
    ) -> list[ValidatedFile]:
        """
        Validate upload request and read file contents.

        This reads each file once and caches the content for later upload,
        avoiding double reads.

        Args:
            project: The project to upload to
            files: List of files to validate

        Returns:
            List of ValidatedFile with cached content

        Raises:
            UploadValidationError: If validation fails
        """
        if not files:
            raise UploadValidationError("No files provided")

        # Get current stats
        current_count, current_size = await self.get_project_upload_stats(project.id)

        # Calculate new totals
        new_file_count = current_count + len(files)
        new_total_size = current_size

        validated_files: list[ValidatedFile] = []

        # Validate and read each file
        for file in files:
            if not file.filename:
                raise UploadValidationError("File without filename provided")

            # Check file type
            if not is_video_file(file.filename, file.content_type):
                raise UploadValidationError(
                    f"Unsupported file type for '{file.filename}'. "
                    f"Supported formats: {', '.join(sorted(VIDEO_EXTENSIONS))}"
                )

            # Read file content once and cache it
            content = await file.read()
            file_size = len(content)

            # Check individual file size
            if file_size > MAX_VIDEO_SIZE_BYTES:
                raise UploadValidationError(
                    f"File '{file.filename}' exceeds maximum size of "
                    f"{MAX_VIDEO_SIZE_BYTES // MB_TO_BYTES}MB"
                )

            # Check for empty file
            if file_size == 0:
                raise UploadValidationError(f"File '{file.filename}' is empty")

            new_total_size += file_size
            validated_files.append(ValidatedFile(file=file, content=content, size=file_size))

        # Check file count limit
        if new_file_count > project.max_videos:
            raise UploadValidationError(
                f"Upload would exceed maximum of {project.max_videos} videos. "
                f"Current: {current_count}, Attempting to add: {len(files)}"
            )

        # Check total size limit
        max_size_bytes = project.max_total_size_mb * MB_TO_BYTES
        if new_total_size > max_size_bytes:
            raise UploadValidationError(
                f"Upload would exceed maximum project size of {project.max_total_size_mb}MB. "
                f"Current: {current_size / MB_TO_BYTES:.1f}MB, "
                f"After upload: {new_total_size / MB_TO_BYTES:.1f}MB"
            )

        return validated_files

    async def upload_files(
        self,
        project: Project,
        files: list[UploadFile],
    ) -> UploadSummary:
        """
        Upload multiple files to a project.

        Args:
            project: The project to upload to
            files: List of files to upload

        Returns:
            UploadSummary with results

        Raises:
            UploadValidationError: If validation fails
        """
        # Validate and read files once
        validated_files = await self.validate_and_read_files(project, files)

        uploaded_files: list[UploadResult] = []
        failed_files: list[dict] = []
        total_size = 0

        for validated in validated_files:
            try:
                result = await self._upload_validated_file(project.id, validated)
                uploaded_files.append(result)
                total_size += result.file_size_bytes
            except Exception as e:
                logger.error(f"Failed to upload file {validated.file.filename}: {e}")
                failed_files.append({
                    "filename": validated.file.filename,
                    "error": str(e),
                })

        # If all files failed, raise an error
        if not uploaded_files and failed_files:
            raise UploadError(
                f"All {len(failed_files)} files failed to upload. "
                f"First error: {failed_files[0]['error']}"
            )

        return UploadSummary(
            project_id=project.id,
            uploaded_files=uploaded_files,
            total_files=len(uploaded_files),
            total_size_bytes=total_size,
            failed_files=failed_files,
        )

    async def _upload_validated_file(
        self,
        project_id: uuid.UUID,
        validated: ValidatedFile,
    ) -> UploadResult:
        """Upload a validated file using cached content."""
        file_id = uuid.uuid4()
        content_type = get_video_content_type(validated.file.filename, validated.file.content_type)

        # Upload to Supabase using cached content
        try:
            storage_path = await self.storage.upload_project_file(
                project_id=project_id,
                file_id=file_id,
                content=validated.content,
                filename=validated.file.filename,
                content_type=content_type,
            )
        except SupabaseStorageError as e:
            raise UploadError(f"Storage upload failed: {e}") from e

        # Get public URL
        file_url = self.storage.get_public_url(
            storage_path, bucket=self.storage.user_uploads_bucket
        )

        # Generate storage filename from the path
        storage_filename = storage_path.split("/")[-1]

        # Create database record
        project_file = ProjectFile(
            id=file_id,
            project_id=project_id,
            filename=storage_filename,
            original_filename=validated.file.filename,
            storage_path=storage_path,
            file_url=file_url,
            file_size_bytes=validated.size,
            content_type=content_type,
            status=ProjectFile.STATUS_PENDING,
        )
        self.db.add(project_file)
        await self.db.flush()

        return UploadResult(
            file_id=file_id,
            filename=storage_filename,
            original_filename=validated.file.filename,
            file_size_bytes=validated.size,
            storage_path=storage_path,
            file_url=file_url,
            status=ProjectFile.STATUS_PENDING,
        )

    async def delete_project_files(self, project_id: uuid.UUID) -> int:
        """
        Delete all files for a project from storage and database.

        Returns:
            Number of files deleted
        """
        # Get all files for project
        result = await self.db.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_id)
        )
        files = result.scalars().all()

        if not files:
            return 0

        # Delete from storage
        try:
            await self.storage.delete_project_files(project_id)
        except SupabaseStorageError as e:
            logger.warning(f"Failed to delete files from storage: {e}")

        # Delete from database (cascade should handle this, but be explicit)
        for file in files:
            await self.db.delete(file)

        return len(files)
