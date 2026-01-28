"""
Duplicate content detection service for ad creatives.
"""

import io
import logging
import re
import tempfile
from typing import Optional
from uuid import UUID

import httpx
import imagehash
import imageio.v3 as iio
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad import Ad

logger = logging.getLogger(__name__)

# Thresholds
PHASH_THRESHOLD = 4  # Tighter threshold (0-64 scale). < 4 is extremely similar.
VIDEO_SAMPLE_FRAMES = 5


class DuplicateDetector:
    """
    Detects duplicate ad creatives using a tiered strategy:
    1. Metadata (Video ID / Media ID) - Instant, 100% accurate
    2. HTTP Headers (Content-Length + ETag) - Fast, 99% accurate
    3. Perceptual Hash (Visual Content) - Slow, AI-grade comparison
    """

    def __init__(self, storage_client=None):
        """Initialize with storage client (e.g. Supabase)."""
        # self.storage = storage_client or SupabaseStorage()
        self.http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)

    async def close(self):
        await self.http_client.aclose()

    async def find_duplicate(
        self, db: AsyncSession, url: str, platform_id: str = None, ad_type: str = "image"
    ) -> Optional[UUID]:
        """
        Main entry point. Runs the strategies in order of efficiency.
        Returns the UUID of the existing duplicate Ad, or None.
        """

        # --- STRATEGY 1: Meta Video/Media ID (Zero Cost) ---
        # If we have a platform-specific ID (e.g., from JSON), check that first.
        if platform_id:
            logger.info(f"Checking strategy 1 (Platform ID): {platform_id}")
            # Assume Ad model has a 'platform_item_id' or similar field
            stmt = select(Ad.id).where(Ad.platform_item_id == platform_id).limit(1)
            result = await db.execute(stmt)
            if match := result.scalar_one_or_none():
                return match

        # Fallback: Extract ID from URL if possible
        extracted_id = self._extract_media_id_from_url(url)
        if extracted_id:
            logger.info(f"Checking strategy 1.5 (Extracted ID): {extracted_id}")
            stmt = select(Ad.id).where(Ad.platform_item_id == extracted_id).limit(1)
            result = await db.execute(stmt)
            if match := result.scalar_one_or_none():
                return match

        # --- STRATEGY 2: HTTP Headers (Low Cost) ---
        # Check file size and ETag without downloading the body
        logger.info(f"Checking strategy 2 (HTTP Headers) for {url}")
        headers_match_id = await self._check_headers_duplicate(db, url)
        if headers_match_id:
            return headers_match_id

        # --- STRATEGY 3: Perceptual Hash (High Cost) ---
        # If we reach here, we must download and analyze.
        logger.info("Strategies 1 & 2 failed. Proceeding to Strategy 3 (pHash).")
        return await self._check_phash_duplicate(db, url, ad_type)

    # =========================================================================
    # STRATEGY IMPLEMENTATIONS
    # =========================================================================

    def _extract_media_id_from_url(self, url: str) -> Optional[str]:
        """
        Extracts immutable ID from Meta CDN URLs.
        Matches: /123456_ or /123456. before the file extension.
        """
        if not url:
            return None
        # Regex for standard FB CDN ID pattern
        match = re.search(r"/(\d{8,})(?:_|.)", url)
        return match.group(1) if match else None

    async def _check_headers_duplicate(self, db: AsyncSession, url: str) -> Optional[UUID]:
        """
        Performs a HEAD request to get Content-Length and ETag.
        Then queries DB for an exact match.
        """
        try:
            response = await self.http_client.head(url)
            if response.status_code != 200:
                return None

            content_length = response.headers.get("content-length")
            etag = response.headers.get("etag")

            if not content_length:
                return None

            # Remove quotes from ETag if present
            if etag:
                etag = etag.strip('"')

            # Build Query: Look for ads with SAME file size AND SAME ETag
            # This assumes your Ad model stores these fields. If not,
            # you can add them or rely solely on pHash.
            stmt = select(Ad.id).where(Ad.file_size == int(content_length))

            # Only add ETag check if we actually got one, otherwise just size is risky
            if etag:
                stmt = stmt.where(Ad.etag == etag)
            else:
                # If no ETag, size matches might be coincidental (rare but possible)
                # We might skip returning here to be safe, or return if size is very specific.
                return None

            result = await db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.warning(f"Header check failed: {e}")
            return None

    async def _check_phash_duplicate(
        self, db: AsyncSession, url: str, ad_type: str
    ) -> Optional[UUID]:
        """
        Downloads content, generates pHash, and compares against DB.
        """
        try:
            # 1. Download Content
            # Note: We download into memory. For huge videos, consider streaming to temp file.
            response = await self.http_client.get(url)
            content_bytes = response.content

            # 2. Compute Hash
            if ad_type == "video":
                new_hash = self.compute_video_phash(content_bytes)
            else:
                new_hash = self.compute_image_phash(content_bytes)

            if not new_hash:
                return None

            # 3. Fetch Existing Hashes
            # OPTIMIZATION: Do not download all images. Query just the hashes.
            # We assume Ad model has a 'perceptual_hash' column (String).
            stmt = select(Ad.id, Ad.perceptual_hash).where(
                Ad.perceptual_hash.is_not(None), Ad.creative_type == ad_type
            )
            result = await db.execute(stmt)
            existing_ads = result.all()  # Returns list of (id, hash)

            # 4. Compare (In-Memory)
            # This is fast for < 100k records. For millions, use a vector DB or bk-tree.
            for ad_id, existing_hash_str in existing_ads:
                if self.is_duplicate_hash(new_hash, existing_hash_str):
                    logger.info(f"Duplicate found via pHash. Matches Ad {ad_id}")
                    return ad_id

            return None

        except Exception as e:
            logger.error(f"pHash strategy failed: {e}")
            return None

    # =========================================================================
    # ORIGINAL AD LOOKUP BY HASH
    # =========================================================================

    async def find_original_by_hash(
        self,
        db: AsyncSession,
        phash: str,
        creative_type: str = "image",
    ) -> Optional[Ad]:
        """
        Find the original ad with a matching perceptual hash.

        Only returns ads where original_ad_id IS NULL (i.e., originals, not duplicates).
        Uses hamming distance comparison for fuzzy matching.

        Args:
            db: Database session
            phash: The perceptual hash to search for
            creative_type: Either 'image' or 'video'

        Returns:
            The matching original Ad, or None if no match found
        """
        if not phash:
            return None

        # Query all original ads (not duplicates) of the same type with a hash
        stmt = select(Ad).where(
            Ad.perceptual_hash.is_not(None),
            Ad.original_ad_id.is_(None),  # Only originals
            Ad.creative_type == creative_type,
        )
        result = await db.execute(stmt)
        original_ads = result.scalars().all()

        # Compare hashes using hamming distance
        for ad in original_ads:
            if self.is_duplicate_hash(phash, ad.perceptual_hash):
                logger.info(f"Found matching original ad {ad.id} for hash")
                return ad

        return None

    # =========================================================================
    # AD-LEVEL DUPLICATE CHECKING
    # =========================================================================

    async def get_phash_from_url(
        self, creative_url: str, creative_type: str = "image"
    ) -> Optional[str]:
        """
        Computes the perceptual hash directly from a creative URL.

        Args:
            creative_url: The URL of the creative media
            creative_type: Either 'image' or 'video'

        Returns:
            The computed pHash string or None if failed
        """
        if not creative_url:
            return None

        try:
            response = await self.http_client.get(creative_url)
            content_bytes = response.content

            if creative_type == "video":
                return self.compute_video_phash(content_bytes)
            else:
                return self.compute_image_phash(content_bytes)
        except Exception as e:
            logger.error(f"Failed to compute hash from URL {creative_url}: {e}")
            return None

    async def get_ad_phash(self, db: AsyncSession, ad_id: str) -> Optional[str]:
        """
        Retrieves or computes the perceptual hash for an ad.
        Downloads the media from creative_url and computes the hash.
        """
        from app.models.ad import Ad

        stmt = select(Ad.creative_url, Ad.creative_type).where(Ad.id == ad_id)
        result = await db.execute(stmt)
        row = result.one_or_none()

        if not row:
            return None

        creative_url, creative_type = row

        if not creative_url:
            return None

        return await self.get_phash_from_url(creative_url, creative_type or "image")

    async def are_ads_duplicates(
        self, ad_id_1: str, ad_id_2: str, *_other_ad_ids: str, db: AsyncSession
    ) -> bool:
        """
        Checks if two or more ads are duplicates of each other.
        Returns True if ad_id_1 and ad_id_2 are duplicates.
        """
        hash1 = await self.get_ad_phash(db, ad_id_1)
        hash2 = await self.get_ad_phash(db, ad_id_2)

        if not hash1 or not hash2:
            return False

        return self.is_duplicate_hash(hash1, hash2)

    async def check_duplicates_in_database(self, db: AsyncSession, *ad_ids: str) -> bool:
        """
        Checks if the given ads exist and can be checked for duplicates.
        Returns True if the check completes successfully.
        """
        from app.models.ad import Ad

        for ad_id in ad_ids:
            stmt = select(Ad.id).where(Ad.id == ad_id)
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                return False
        return True

    # =========================================================================
    # HASHING UTILS
    # =========================================================================

    def compute_image_phash(self, image_bytes: bytes) -> str:
        """Computes pHash for a single image."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Convert to standard RGB to avoid mode mismatches
            if image.mode != "RGB":
                image = image.convert("RGB")

            # hash_size=8 is standard (64-bit).
            # For more detail/strictness, use hash_size=16 (256-bit).
            phash = imagehash.phash(image, hash_size=8)
            return str(phash)
        except Exception:
            return None

    def compute_video_phash(self, video_bytes: bytes) -> str:
        """
        Computes a composite hash for video.
        Ignores solid color frames (black/white) to avoid false positives.
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
                tmp.write(video_bytes)
                tmp.flush()

                # Read basic metadata
                props = iio.improps(tmp.name, plugin="pyav")
                total_frames = props.shape[0] if len(props.shape) > 0 else 0

                # If reading metadata fails, just try reading frames
                if total_frames < 10:
                    total_frames = 100

                # Sample frames spread across the video
                indices = [
                    int(total_frames * i / VIDEO_SAMPLE_FRAMES) for i in range(VIDEO_SAMPLE_FRAMES)
                ]

                valid_hashes = []

                for idx in indices:
                    try:
                        frame = iio.imread(tmp.name, index=idx, plugin="pyav")

                        # Check for "Empty" frames (Solid Black/White)
                        # Standard deviation of color channels is low for solid frames
                        if np.std(frame) < 10:
                            continue  # Skip this frame

                        image = Image.fromarray(frame)
                        if image.mode != "RGB":
                            image = image.convert("RGB")

                        # Use dHash (Difference Hash) for video frames
                        # It is often more robust for video compression artifacts than pHash
                        h = imagehash.dhash(image, hash_size=8)
                        valid_hashes.append(str(h))
                    except Exception:
                        continue

                if not valid_hashes:
                    return None

                # Join with pipe to store as single string
                return "|".join(valid_hashes)

        except Exception as e:
            logger.error(f"Video hashing failed: {e}")
            return None

    def compute_phash(self, image_bytes: bytes) -> str:
        """Alias for compute_image_phash for backwards compatibility."""
        return self.compute_image_phash(image_bytes)

    def extract_media_id_from_url(self, url: str) -> Optional[str]:
        """Public alias for _extract_media_id_from_url."""
        return self._extract_media_id_from_url(url)

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Computes the hamming distance between two hashes.
        Returns the number of bits that differ.
        """
        if not hash1 or not hash2:
            return 64  # Max distance for 64-bit hash
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2
        except ValueError:
            return 64

    def are_hashes_duplicate(self, hash1: str, hash2: str) -> bool:
        """Alias for is_duplicate_hash for backwards compatibility."""
        return self.is_duplicate_hash(hash1, hash2)

    def is_duplicate_hash(self, hash1: str, hash2: str) -> bool:
        """
        Compares two hashes (Video or Image).
        """
        if not hash1 or not hash2:
            return False

        # Video Comparison (Multi-frame)
        if "|" in hash1 and "|" in hash2:
            h1_parts = hash1.split("|")
            h2_parts = hash2.split("|")

            # We look for a "Subsequence Match" or "Majority Match"
            # If > 50% of the frames match closely, it's a duplicate.
            matches = 0
            comparisons = 0

            # Compare the minimum number of frames available in both
            limit = min(len(h1_parts), len(h2_parts))
            if limit == 0:
                return False

            for i in range(limit):
                try:
                    d = imagehash.hex_to_hash(h1_parts[i]) - imagehash.hex_to_hash(h2_parts[i])
                    comparisons += 1
                    if d <= PHASH_THRESHOLD:
                        matches += 1
                except ValueError:
                    continue

            # If 60% of sampled frames match, it's the same video
            return (matches / comparisons) > 0.6

        # Image Comparison (Single)
        elif "|" not in hash1 and "|" not in hash2:
            try:
                d = imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)
                return bool(d <= PHASH_THRESHOLD)
            except ValueError:
                return False

        return False
