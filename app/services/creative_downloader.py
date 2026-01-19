"""Creative downloader service for downloading and storing ad creatives."""

import asyncio
import logging
from uuid import UUID

import httpx

from app.config import get_settings
from app.services.ad_library_scraper import AdLibraryScraper
from app.utils.supabase_storage import SupabaseStorage, download_from_url

logger = logging.getLogger(__name__)


class CreativeDownloadError(Exception):
    """Exception raised when creative download fails."""

    pass


class CreativeDownloader:
    """Downloads and stores ad creatives from Meta Ad Library."""

    def __init__(self) -> None:
        """Initialize the creative downloader."""
        settings = get_settings()
        self.storage = SupabaseStorage()
        self.scraper = AdLibraryScraper()
        self.max_retries = 3
        self.retry_delay = 2

    async def download_creative(
        self,
        ad_snapshot_url: str,
        competitor_id: UUID,
        ad_id: str,
    ) -> tuple[str, str]:
        """
        Download a creative from Meta and store it in Supabase.

        Args:
            ad_snapshot_url: URL of the ad snapshot page
            competitor_id: UUID of the competitor
            ad_id: Ad Library ID

        Returns:
            Tuple of (storage_path, creative_type)
        """
        creative_url, creative_type = await self.scraper.get_creative_url_from_snapshot(
            ad_snapshot_url
        )

        if not creative_url or creative_type == "unknown":
            raise CreativeDownloadError(f"Could not determine creative URL from snapshot: {ad_snapshot_url}")

        for attempt in range(self.max_retries):
            try:
                content, content_type = await download_from_url(creative_url)

                extension = self._get_extension(content_type, creative_type)

                storage_path = await self.storage.upload_creative(
                    competitor_id=competitor_id,
                    ad_id=ad_id,
                    content=content,
                    creative_type=creative_type,
                    file_extension=extension,
                )

                logger.info(f"Successfully downloaded creative for ad {ad_id}")
                return storage_path, creative_type

            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed for ad {ad_id}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise CreativeDownloadError(
                        f"Failed to download creative after {self.max_retries} attempts: {e}"
                    ) from e

        raise CreativeDownloadError("Download failed - should not reach here")

    def _get_extension(self, content_type: str | None, creative_type: str) -> str:
        """Determine file extension from content type."""
        if content_type:
            content_type = content_type.lower()
            if "jpeg" in content_type or "jpg" in content_type:
                return "jpg"
            if "png" in content_type:
                return "png"
            if "webp" in content_type:
                return "webp"
            if "gif" in content_type:
                return "gif"
            if "mp4" in content_type:
                return "mp4"
            if "webm" in content_type:
                return "webm"
            if "quicktime" in content_type or "mov" in content_type:
                return "mov"

        return "jpg" if creative_type == "image" else "mp4"

    async def download_multiple(
        self,
        ads: list[dict],
        competitor_id: UUID,
        concurrency: int = 3,
    ) -> dict[str, tuple[str, str] | None]:
        """
        Download multiple creatives concurrently.

        Args:
            ads: List of ad dictionaries with ad_library_id and ad_snapshot_url
            competitor_id: UUID of the competitor
            concurrency: Maximum concurrent downloads

        Returns:
            Dictionary mapping ad_library_id to (storage_path, creative_type) or None if failed
        """
        results: dict[str, tuple[str, str] | None] = {}
        semaphore = asyncio.Semaphore(concurrency)

        async def download_with_limit(ad: dict) -> tuple[str, tuple[str, str] | None]:
            ad_id = ad["ad_library_id"]
            snapshot_url = ad.get("ad_snapshot_url")

            if not snapshot_url:
                logger.warning(f"No snapshot URL for ad {ad_id}")
                return ad_id, None

            async with semaphore:
                try:
                    result = await self.download_creative(snapshot_url, competitor_id, ad_id)
                    return ad_id, result
                except CreativeDownloadError as e:
                    logger.error(f"Failed to download creative for ad {ad_id}: {e}")
                    return ad_id, None

        tasks = [download_with_limit(ad) for ad in ads]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, Exception):
                logger.error(f"Unexpected error during download: {result}")
            else:
                ad_id, download_result = result
                results[ad_id] = download_result

        return results

    async def verify_creative_exists(self, storage_path: str) -> bool:
        """
        Verify that a creative exists in storage.

        Args:
            storage_path: Path to the creative in storage

        Returns:
            True if the creative exists, False otherwise
        """
        return await self.storage.file_exists(storage_path)
