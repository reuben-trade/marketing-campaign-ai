"""Reference ad service for uploading and analyzing user-provided reference ads."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad import Ad
from app.models.competitor import Competitor
from app.schemas.recipe import ReferenceAdResponse
from app.services.recipe_extractor import RecipeExtractionError, RecipeExtractor
from app.services.video_analyzer import VideoAnalysisError, VideoAnalyzer
from app.utils.supabase_storage import SupabaseStorage, download_from_url

logger = logging.getLogger(__name__)

# Fixed UUID for the "Reference Ads" competitor
REFERENCE_ADS_COMPETITOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
REFERENCE_ADS_PAGE_ID = "reference-ads"


class ReferenceAdError(Exception):
    """Exception raised when reference ad processing fails."""

    pass


class ReferenceAdService:
    """Service for handling user-uploaded reference ads."""

    def __init__(self) -> None:
        """Initialize the service."""
        self.storage = SupabaseStorage()
        self.video_analyzer = VideoAnalyzer()
        self.recipe_extractor = RecipeExtractor()

    async def _ensure_reference_competitor(self, db: AsyncSession) -> Competitor:
        """Ensure the Reference Ads competitor exists, creating if needed."""
        result = await db.execute(
            select(Competitor).where(Competitor.page_id == REFERENCE_ADS_PAGE_ID)
        )
        competitor = result.scalar_one_or_none()

        if not competitor:
            competitor = Competitor(
                id=REFERENCE_ADS_COMPETITOR_ID,
                company_name="Reference Ads",
                page_id=REFERENCE_ADS_PAGE_ID,
                industry="Reference",
                discovery_method="user_upload",
                active=True,
            )
            db.add(competitor)
            await db.commit()
            await db.refresh(competitor)
            logger.info("Created Reference Ads competitor")

        return competitor

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename. Delegates to storage helper."""
        return self.storage._get_content_type(filename)

    async def upload_reference_ad(
        self,
        db: AsyncSession,
        file_content: bytes,
        filename: str,
        custom_name: str | None = None,
    ) -> ReferenceAdResponse:
        """
        Upload and analyze a reference ad video.

        Args:
            db: Database session
            file_content: Video file content as bytes
            filename: Original filename
            custom_name: Optional custom name for the recipe

        Returns:
            ReferenceAdResponse with created ad and recipe
        """
        notes: list[str] = []
        ad_id = uuid.uuid4()
        ad_library_id = f"ref-{ad_id.hex[:16]}"

        try:
            # Ensure reference competitor exists
            competitor = await self._ensure_reference_competitor(db)
            notes.append("Reference competitor ready")

            # Upload to storage
            extension = Path(filename).suffix or ".mp4"
            storage_path = f"reference-ads/{ad_id}{extension}"
            await self.storage.upload_bytes(
                content=file_content,
                storage_path=storage_path,
                bucket=self.storage.ad_creatives_bucket,
                content_type=self._get_mime_type(filename),
            )
            notes.append(f"Uploaded to storage: {storage_path}")

            # Analyze video
            try:
                mime_type = self._get_mime_type(filename)
                raw_analysis = await self.video_analyzer.analyze_video_v2(
                    video_content=file_content,
                    competitor_name="Reference Ad",
                    market_position="reference",
                    mime_type=mime_type,
                )
                video_intelligence = self.video_analyzer.parse_enhanced_analysis_v2(
                    raw_analysis
                ).model_dump()
                notes.append("Video analysis complete")
            except VideoAnalysisError as e:
                logger.error(f"Video analysis failed: {e}")
                notes.append(f"Video analysis failed: {e}")
                video_intelligence = None

            # Create ad record
            ad = Ad(
                id=ad_id,
                competitor_id=competitor.id,
                ad_library_id=ad_library_id,
                creative_type="video",
                creative_storage_path=storage_path,
                creative_url=self.storage.get_public_url(
                    storage_path, self.storage.ad_creatives_bucket
                ),
                ad_headline=custom_name or f"Reference Ad {ad_id.hex[:8]}",
                video_intelligence=video_intelligence,
                analyzed=video_intelligence is not None,
                analyzed_date=datetime.now(timezone.utc) if video_intelligence else None,
                download_status="completed",
                analysis_status="completed" if video_intelligence else "failed",
                publication_date=datetime.now(timezone.utc),
            )
            db.add(ad)
            await db.commit()
            await db.refresh(ad)
            notes.append(f"Created ad record: {ad_id}")

            # Extract recipe if analysis succeeded
            recipe_response = None
            if video_intelligence:
                try:
                    extract_result = await self.recipe_extractor.extract_from_ad(
                        db, ad_id, custom_name
                    )
                    recipe_response = extract_result.recipe
                    notes.extend(extract_result.extraction_notes)
                except RecipeExtractionError as e:
                    logger.error(f"Recipe extraction failed: {e}")
                    notes.append(f"Recipe extraction failed: {e}")

            status = "success" if recipe_response else "partial"
            message = (
                "Reference ad processed and recipe extracted"
                if recipe_response
                else "Reference ad uploaded but recipe extraction failed"
            )

            return ReferenceAdResponse(
                ad_id=ad_id,
                recipe=recipe_response,
                status=status,
                message=message,
                processing_notes=notes,
            )

        except Exception as e:
            logger.error(f"Reference ad upload failed: {e}")
            raise ReferenceAdError(f"Failed to process reference ad: {e}") from e

    async def fetch_from_url(
        self,
        db: AsyncSession,
        url: str,
        custom_name: str | None = None,
    ) -> ReferenceAdResponse:
        """
        Fetch and analyze a reference ad from URL.

        Args:
            db: Database session
            url: URL to fetch the video from
            custom_name: Optional custom name for the recipe

        Returns:
            ReferenceAdResponse with created ad and recipe
        """
        notes: list[str] = []

        try:
            # Download video from URL
            notes.append("Fetching video from URL...")
            try:
                content, content_type = await download_from_url(url, timeout=180)
                notes.append(f"Downloaded {len(content) / 1024 / 1024:.2f} MB")
            except Exception as e:
                raise ReferenceAdError(f"Failed to download video: {e}") from e

            # Determine file extension from content type or URL
            extension = ".mp4"
            if content_type:
                if "webm" in content_type:
                    extension = ".webm"
                elif "quicktime" in content_type or "mov" in content_type:
                    extension = ".mov"
            elif url:
                url_path = url.split("?")[0]
                if url_path.endswith(".webm"):
                    extension = ".webm"
                elif url_path.endswith(".mov"):
                    extension = ".mov"

            filename = f"fetched{extension}"

            # Use the upload method to process
            return await self.upload_reference_ad(db, content, filename, custom_name)

        except ReferenceAdError:
            raise
        except Exception as e:
            logger.error(f"URL fetch failed: {e}")
            raise ReferenceAdError(f"Failed to fetch from URL: {e}") from e
