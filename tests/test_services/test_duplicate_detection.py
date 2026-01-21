"""Tests for duplicate content detection service.

These tests run against the REAL database and Supabase storage
to verify the pipeline works in production.

Test ad IDs:
- a3ac3d83-2439-489e-91d3-cb37cb583951 = unique
- 9d67e061-f352-4212-bcd3-146a410ec7da = duplicate
- 4455b2f5-7545-4fa8-9b2f-037bed8df73d = duplicate (same as above)
"""

import pytest

from app.database import async_session_maker
from app.services.duplicate_detection import DuplicateDetector

# Test ad IDs from real database
UNIQUE_AD = "a3ac3d83-2439-489e-91d3-cb37cb583951"
DUPLICATE_1 = "9d67e061-f352-4212-bcd3-146a410ec7da"
DUPLICATE_2 = "4455b2f5-7545-4fa8-9b2f-037bed8df73d"


@pytest.fixture
def detector():
    """Create a DuplicateDetector instance."""
    return DuplicateDetector()


@pytest.fixture
async def db():
    """Get a real database session."""
    async with async_session_maker() as session:
        yield session


class TestDuplicateDetection:
    """Tests for duplicate content detection using pHash against real data."""

    @pytest.mark.asyncio
    async def test_duplicate_pair_detected(self, detector: DuplicateDetector, db):
        """
        Test that known duplicate ads are correctly identified.

        Ads DUPLICATE_1 and DUPLICATE_2 should be detected as duplicates.
        """
        result = await detector.are_ads_duplicates(
            DUPLICATE_1, DUPLICATE_2, UNIQUE_AD, db=db
        )

        # Should return True because DUPLICATE_1 and DUPLICATE_2 are duplicates
        assert result is True

    @pytest.mark.asyncio
    async def test_unique_ad_not_duplicate_of_pair(self, detector: DuplicateDetector, db):
        """
        Test that the unique ad is not flagged as a duplicate of the duplicate pair.
        """
        # Get hashes for comparison
        unique_hash = await detector.get_ad_phash(db, UNIQUE_AD)
        dup_hash = await detector.get_ad_phash(db, DUPLICATE_1)

        assert unique_hash is not None, f"Could not get hash for unique ad {UNIQUE_AD}"
        assert dup_hash is not None, f"Could not get hash for duplicate ad {DUPLICATE_1}"

        # The unique ad should NOT match the duplicate pair
        is_dup = detector.are_hashes_duplicate(unique_hash, dup_hash)
        assert is_dup is False, "Unique ad incorrectly flagged as duplicate"

    @pytest.mark.asyncio
    async def test_duplicate_pair_hashes_match(self, detector: DuplicateDetector, db):
        """
        Test that the two known duplicates have matching hashes.
        """
        hash1 = await detector.get_ad_phash(db, DUPLICATE_1)
        hash2 = await detector.get_ad_phash(db, DUPLICATE_2)

        assert hash1 is not None, f"Could not get hash for {DUPLICATE_1}"
        assert hash2 is not None, f"Could not get hash for {DUPLICATE_2}"

        distance = detector.hamming_distance(hash1, hash2)
        print(f"Hamming distance between duplicates: {distance}")

        assert detector.are_hashes_duplicate(hash1, hash2), (
            f"Known duplicates not detected. Distance: {distance}"
        )

    @pytest.mark.asyncio
    async def test_check_duplicates_in_database(self, detector: DuplicateDetector, db):
        """
        Test database duplicate checking with known test ads.
        """
        result = await detector.check_duplicates_in_database(
            db, UNIQUE_AD, DUPLICATE_1, DUPLICATE_2
        )
        assert result is True


class TestPHashComputation:
    """Unit tests for pHash computation methods (no DB required)."""

    def test_identical_images_have_zero_distance(self, detector: DuplicateDetector):
        """Identical images should have hamming distance of 0."""
        from io import BytesIO

        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()

        hash1 = detector.compute_phash(image_bytes)
        hash2 = detector.compute_phash(image_bytes)

        assert detector.hamming_distance(hash1, hash2) == 0
        assert detector.are_hashes_duplicate(hash1, hash2) is True

    def test_different_images_have_nonzero_distance(self, detector: DuplicateDetector):
        """Different images should have some hamming distance."""
        from io import BytesIO

        from PIL import Image, ImageDraw

        # Create image with pattern
        img1 = Image.new("RGB", (100, 100), color="white")
        draw1 = ImageDraw.Draw(img1)
        draw1.rectangle([10, 10, 50, 50], fill="red")
        buffer1 = BytesIO()
        img1.save(buffer1, format="PNG")

        # Create different image
        img2 = Image.new("RGB", (100, 100), color="black")
        draw2 = ImageDraw.Draw(img2)
        draw2.ellipse([60, 60, 90, 90], fill="blue")
        buffer2 = BytesIO()
        img2.save(buffer2, format="PNG")

        hash1 = detector.compute_phash(buffer1.getvalue())
        hash2 = detector.compute_phash(buffer2.getvalue())

        distance = detector.hamming_distance(hash1, hash2)
        print(f"Distance between different images: {distance}")
        assert distance > 0


class TestMediaIdExtraction:
    """Tests for Meta CDN media ID extraction."""

    def test_extract_media_id_from_standard_url(self, detector: DuplicateDetector):
        """Test extraction from standard Meta CDN URL."""
        url = "https://scontent.xx.fbcdn.net/v/t39.30808-6/456789123_something.jpg"
        media_id = detector.extract_media_id_from_url(url)
        assert media_id == "456789123"

    def test_extract_media_id_from_url_with_extension(self, detector: DuplicateDetector):
        """Test extraction when ID is followed by extension."""
        url = "https://scontent.xx.fbcdn.net/v/t39.30808-6/123456789012.jpg"
        media_id = detector.extract_media_id_from_url(url)
        assert media_id == "123456789012"

    def test_extract_media_id_returns_none_for_invalid_url(self, detector: DuplicateDetector):
        """Test that invalid URLs return None."""
        url = "https://example.com/image.jpg"
        media_id = detector.extract_media_id_from_url(url)
        assert media_id is None

    def test_extract_media_id_returns_none_for_empty_url(self, detector: DuplicateDetector):
        """Test that empty/None URLs return None."""
        assert detector.extract_media_id_from_url("") is None
        assert detector.extract_media_id_from_url(None) is None
