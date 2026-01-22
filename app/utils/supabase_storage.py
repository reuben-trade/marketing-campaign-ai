"""Supabase Storage utilities."""

import hashlib
import mimetypes
from pathlib import Path
from uuid import UUID

import httpx
from supabase import Client, create_client

from app.config import get_settings


class SupabaseStorageError(Exception):
    """Exception raised for Supabase storage errors."""

    pass


class SupabaseStorage:
    """Supabase Storage client for managing ad creatives and documents."""

    def __init__(self) -> None:
        """Initialize Supabase client."""
        settings = get_settings()
        self.client: Client = create_client(settings.supabase_url, settings.supabase_key)
        self.ad_creatives_bucket = settings.ad_creatives_bucket
        self.strategy_documents_bucket = settings.strategy_documents_bucket

    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename."""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"

    async def upload_creative(
        self,
        competitor_id: UUID,
        ad_id: str,
        content: bytes,
        creative_type: str,
        file_extension: str | None = None,
    ) -> str:
        """
        Upload an ad creative to Supabase Storage.

        Args:
            competitor_id: UUID of the competitor
            ad_id: Ad Library ID
            content: File content as bytes
            creative_type: "image" or "video"
            file_extension: Optional file extension (e.g., "jpg", "mp4")

        Returns:
            Storage path of the uploaded file
        """
        if file_extension is None:
            file_extension = "jpg" if creative_type == "image" else "mp4"

        subfolder = "images" if creative_type == "image" else "videos"
        storage_path = f"competitors/{competitor_id}/{subfolder}/{ad_id}.{file_extension}"

        content_type = (
            f"image/{file_extension}" if creative_type == "image" else f"video/{file_extension}"
        )

        try:
            self.client.storage.from_(self.ad_creatives_bucket).upload(
                path=storage_path,
                file=content,
                file_options={"content-type": content_type},
            )
            return storage_path
        except Exception as e:
            # Check if it's a duplicate error (409) - treat as success since file exists
            error_str = str(e)
            if "409" in error_str or "Duplicate" in error_str or "already exists" in error_str:
                return storage_path
            raise SupabaseStorageError(f"Failed to upload creative: {e}") from e

    async def upload_strategy_document(
        self,
        strategy_id: UUID,
        content: bytes,
        filename: str,
    ) -> str:
        """
        Upload a strategy document (PDF) to Supabase Storage.

        Args:
            strategy_id: UUID of the business strategy
            content: File content as bytes
            filename: Original filename

        Returns:
            Storage path of the uploaded file
        """
        extension = Path(filename).suffix or ".pdf"
        storage_path = f"{strategy_id}{extension}"

        try:
            self.client.storage.from_(self.strategy_documents_bucket).upload(
                path=storage_path,
                file=content,
                file_options={"content-type": "application/pdf"},
            )
            return storage_path
        except Exception as e:
            raise SupabaseStorageError(f"Failed to upload document: {e}") from e

    def get_public_url(self, storage_path: str, bucket: str | None = None) -> str:
        """
        Get the public URL for a file in storage.

        Args:
            storage_path: Path to the file in storage
            bucket: Bucket name (defaults to ad_creatives_bucket)

        Returns:
            Public URL for the file
        """
        bucket = bucket or self.ad_creatives_bucket
        response = self.client.storage.from_(bucket).get_public_url(storage_path)
        return response

    async def download_file(self, storage_path: str, bucket: str | None = None) -> bytes:
        """
        Download a file from Supabase Storage.

        Args:
            storage_path: Path to the file in storage
            bucket: Bucket name (defaults to ad_creatives_bucket)

        Returns:
            File content as bytes
        """
        bucket = bucket or self.ad_creatives_bucket
        try:
            response = self.client.storage.from_(bucket).download(storage_path)
            return response
        except Exception as e:
            raise SupabaseStorageError(f"Failed to download file: {e}") from e

    async def delete_file(self, storage_path: str, bucket: str | None = None) -> None:
        """
        Delete a file from Supabase Storage.

        Args:
            storage_path: Path to the file in storage
            bucket: Bucket name (defaults to ad_creatives_bucket)
        """
        bucket = bucket or self.ad_creatives_bucket
        try:
            self.client.storage.from_(bucket).remove([storage_path])
        except Exception as e:
            raise SupabaseStorageError(f"Failed to delete file: {e}") from e

    async def file_exists(self, storage_path: str, bucket: str | None = None) -> bool:
        """
        Check if a file exists in storage.

        Args:
            storage_path: Path to the file in storage
            bucket: Bucket name (defaults to ad_creatives_bucket)

        Returns:
            True if file exists, False otherwise
        """
        bucket = bucket or self.ad_creatives_bucket
        try:
            folder = "/".join(storage_path.split("/")[:-1])
            filename = storage_path.split("/")[-1]
            response = self.client.storage.from_(bucket).list(folder)
            return any(f["name"] == filename for f in response)
        except Exception:
            return False

    async def upload_bytes(
        self,
        content: bytes,
        storage_path: str,
        bucket: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload bytes content to Supabase Storage.

        Args:
            content: File content as bytes
            storage_path: Path where to store the file
            bucket: Bucket name
            content_type: MIME type of the content

        Returns:
            Storage path of the uploaded file
        """
        try:
            self.client.storage.from_(bucket).upload(
                path=storage_path,
                file=content,
                file_options={"content-type": content_type},
            )
            return storage_path
        except Exception as e:
            raise SupabaseStorageError(f"Failed to upload bytes: {e}") from e


async def download_from_url(url: str, timeout: int = 120) -> tuple[bytes, str | None]:
    """
    Download content from a URL.

    Args:
        url: URL to download from
        timeout: Request timeout in seconds

    Returns:
        Tuple of (content bytes, content type)
    """
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type")
        return response.content, content_type


def get_file_hash(content: bytes) -> str:
    """Generate SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()
