"""Upload service for handling project file uploads."""

import logging
import uuid
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_file import ProjectFile
from app.utils.supabase_storage import SupabaseStorage, SupabaseStorageError

logger = logging.getLogger(__name__)

# Supported video file types
VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "avi", "m4v", "mkv"}
VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
    "video/x-m4v",
    "video/x-matroska",
}

# File size limits
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB per file
MB_TO_BYTES = 1024 * 1024


class UploadError(Exception):
    """Exception raised for upload errors."""

    pass


class UploadValidationError(UploadError):
    """Exception raised for upload validation errors."""

    pass


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
    uploaded_files: list[UploadResult]
    total_files: int
    total_size_bytes: int
    failed_files: list[dict]


def is_video_file(filename: str, content_type: str | None) -> bool:
    """Check if file is a supported video format."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return extension in VIDEO_EXTENSIONS or content_type in VIDEO_MIME_TYPES


def get_content_type(filename: str, provided_content_type: str | None) -> str:
    """Get the content type for a file."""
    if provided_content_type and provided_content_type in VIDEO_MIME_TYPES:
        return provided_content_type

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    extension_to_mime = {
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "webm": "video/webm",
        "avi": "video/x-msvideo",
        "m4v": "video/x-m4v",
        "mkv": "video/x-matroska",
    }
    return extension_to_mime.get(extension, "video/mp4")


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

    async def validate_upload(
        self,
        project: Project,
        files: list[UploadFile],
    ) -> None:
        """
        Validate upload request against project constraints.

        Raises:
            UploadValidationError: If validation fails
        """
        # Check if any files provided
        if not files:
            raise UploadValidationError("No files provided")

        # Get current stats
        current_count, current_size = await self.get_project_upload_stats(project.id)

        # Calculate new totals
        new_file_count = current_count + len(files)
        new_total_size = current_size

        # Validate each file
        for file in files:
            if not file.filename:
                raise UploadValidationError("File without filename provided")

            # Check file type
            if not is_video_file(file.filename, file.content_type):
                raise UploadValidationError(
                    f"Unsupported file type for '{file.filename}'. "
                    f"Supported formats: {', '.join(sorted(VIDEO_EXTENSIONS))}"
                )

            # Read file to get size (we need to do this anyway for upload)
            content = await file.read()
            await file.seek(0)  # Reset for later reading

            file_size = len(content)

            # Check individual file size
            if file_size > MAX_FILE_SIZE_BYTES:
                raise UploadValidationError(
                    f"File '{file.filename}' exceeds maximum size of "
                    f"{MAX_FILE_SIZE_BYTES // MB_TO_BYTES}MB"
                )

            # Check for empty file
            if file_size == 0:
                raise UploadValidationError(f"File '{file.filename}' is empty")

            new_total_size += file_size

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
        # Validate first
        await self.validate_upload(project, files)

        uploaded_files: list[UploadResult] = []
        failed_files: list[dict] = []
        total_size = 0

        for file in files:
            try:
                result = await self._upload_single_file(project.id, file)
                uploaded_files.append(result)
                total_size += result.file_size_bytes
            except Exception as e:
                logger.error(f"Failed to upload file {file.filename}: {e}")
                failed_files.append({
                    "filename": file.filename,
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

    async def _upload_single_file(
        self,
        project_id: uuid.UUID,
        file: UploadFile,
    ) -> UploadResult:
        """Upload a single file."""
        file_id = uuid.uuid4()
        content = await file.read()
        file_size = len(content)
        content_type = get_content_type(file.filename, file.content_type)

        # Generate storage filename (sanitized)
        extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "mp4"
        storage_filename = f"{file_id}.{extension}"

        # Upload to Supabase
        try:
            storage_path = await self.storage.upload_project_file(
                project_id=project_id,
                file_id=file_id,
                content=content,
                filename=file.filename,
                content_type=content_type,
            )
        except SupabaseStorageError as e:
            raise UploadError(f"Storage upload failed: {e}") from e

        # Get public URL
        file_url = self.storage.get_public_url(
            storage_path, bucket=self.storage.user_uploads_bucket
        )

        # Create database record
        project_file = ProjectFile(
            id=file_id,
            project_id=project_id,
            filename=storage_filename,
            original_filename=file.filename,
            storage_path=storage_path,
            file_url=file_url,
            file_size_bytes=file_size,
            content_type=content_type,
            status=ProjectFile.STATUS_PENDING,
        )
        self.db.add(project_file)
        await self.db.flush()

        return UploadResult(
            file_id=file_id,
            filename=storage_filename,
            original_filename=file.filename,
            file_size_bytes=file_size,
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
