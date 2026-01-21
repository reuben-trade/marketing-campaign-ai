"""Tests for duplicate content detection service.

These tests use creative URLs directly - no database lookup required.
To add new test cases, simply add creative URLs below.
"""

import pytest

from app.services.duplicate_detection import DuplicateDetector

# =============================================================================
# TEST CREATIVE URLs
# Add your test creative URLs here directly - no database lookup required
# =============================================================================

# # Two URLs that should be detected as duplicates (same/similar creative)
# DUPLICATE_URL_1 = "https://video.xx.fbcdn.net/o1/v/t2/f2/m367/AQPd5TSD2LyptPII0GDm4CYfn1jbjToYJhFQprIOdqvxxE1SBuYV7UFjKTL6yl0XISPGQGJfsW4s2pOxlniVteKQkli-N1N1w3K1zFjBwg.mp4?_nc_cat=106&_nc_oc=AdkHO4Tl5tdKe3mT_3QNIko4VVhGMEo9RljMRJMrLx10cR6Mzy8noQtJBxDGsHX7EYc&_nc_sid=8bf8fe&_nc_ht=video.fper13-1.fna.fbcdn.net&_nc_ohc=YzZ3BKj_GA8Q7kNvwFU0odF&efg=eyJ2ZW5jb2RlX3RhZyI6Inhwdl9wcm9ncmVzc2l2ZS5WSV9VU0VDQVNFX1BST0RVQ1RfVFlQRS4uQzMuMzYwLnByb2dyZXNzaXZlX2gyNjQtYmFzaWMtZ2VuMl8zNjBwIiwieHB2X2Fzc2V0X2lkIjoxNzkzOTA4NDM0MzExMjE5NSwiYXNzZXRfYWdlX2RheXMiOjEsInZpX3VzZWNhc2VfaWQiOjEwMDk5LCJkdXJhdGlvbl9zIjozOCwidXJsZ2VuX3NvdXJjZSI6Ind3dyJ9&ccb=17-1&_nc_gid=0Xuux6TX_lMbutP61KaSQQ&_nc_zt=28&oh=00_AfqbEQpio5E1V8n3cZvLizqc21xbfCUmzMhQokxTiipHbQ&oe=69763548"
# DUPLICATE_URL_2 = "https://video.xx.fbcdn.net/o1/v/t2/f2/m367/AQPd5TSD2LyptPII0GDm4CYfn1jbjToYJhFQprIOdqvxxE1SBuYV7UFjKTL6yl0XISPGQGJfsW4s2pOxlniVteKQkli-N1N1w3K1zFjBwg.mp4?_nc_cat=106&_nc_oc=AdkHO4Tl5tdKe3mT_3QNIko4VVhGMEo9RljMRJMrLx10cR6Mzy8noQtJBxDGsHX7EYc&_nc_sid=8bf8fe&_nc_ht=video.fper13-1.fna.fbcdn.net&_nc_ohc=YzZ3BKj_GA8Q7kNvwFU0odF&efg=eyJ2ZW5jb2RlX3RhZyI6Inhwdl9wcm9ncmVzc2l2ZS5WSV9VU0VDQVNFX1BST0RVQ1RfVFlQRS4uQzMuMzYwLnByb2dyZXNzaXZlX2gyNjQtYmFzaWMtZ2VuMl8zNjBwIiwieHB2X2Fzc2V0X2lkIjoxNzkzOTA4NDM0MzExMjE5NSwiYXNzZXRfYWdlX2RheXMiOjEsInZpX3VzZWNhc2VfaWQiOjEwMDk5LCJkdXJhdGlvbl9zIjozOCwidXJsZ2VuX3NvdXJjZSI6Ind3dyJ9&ccb=17-1&_nc_gid=0Xuux6TX_lMbutP61KaSQQ&_nc_zt=28&oh=00_AfqbEQpio5E1V8n3cZvLizqc21xbfCUmzMhQokxTiipHbQ&oe=69763548"

# # A URL that should NOT match the duplicates above
# UNIQUE_URL = "https://video.xx.fbcdn.net/o1/v/t2/f2/m366/AQODqkIhM0tq2FBzdbdW1kMHTLxFwy2A6KGctyYC5kt72C1AJu1c-JB2wM8P9WlVu3yhJKgiN-U8J2HMWgGTckL9LEVCxnY_b7p5FQJeT-pqxA.mp4?_nc_cat=100&_nc_oc=AdkGf2Hdn9eSTLw2wFQdwqqp3AGHzuA-DumtDda_hgOCGrrLjHdmNZNL77xq8fB0DzY&_nc_sid=5e9851&_nc_ht=video.fper13-1.fna.fbcdn.net&_nc_ohc=z6ukyBv4D8AQ7kNvwF1-sBq&efg=eyJ2ZW5jb2RlX3RhZyI6Inhwdl9wcm9ncmVzc2l2ZS5WSV9VU0VDQVNFX1BST0RVQ1RfVFlQRS4uQzMuNzIwLmRhc2hfaDI2NC1iYXNpYy1nZW4yXzcyMHAiLCJ4cHZfYXNzZXRfaWQiOjQyMDA2ODc0NzY4NzA1ODEsImFzc2V0X2FnZV9kYXlzIjozNCwidmlfdXNlY2FzZV9pZCI6MTA3OTksImR1cmF0aW9uX3MiOjQwLCJ1cmxnZW5fc291cmNlIjoid3d3In0%3D&ccb=17-1&vs=33af0fb628b2b574&_nc_vs=HBksFQIYRWZiX2VwaGVtZXJhbC9GMzRGOUU5MkU3NzM3QTA0ODFBRjA4QjZGNzY5RUI4RV9tdF8xX3ZpZGVvX2Rhc2hpbml0Lm1wNBUAAsgBEgAVAhhAZmJfcGVybWFuZW50LzIyNDg4QUFCOUY1MEYzNzVDOTIzNDIzNzFEMTUzMEI5X2F1ZGlvX2Rhc2hpbml0Lm1wNBUCAsgBEgAoABgAGwKIB3VzZV9vaWwBMRJwcm9ncmVzc2l2ZV9yZWNpcGUBMRUAACbqtvjNmKD2DhUCKAJDMywXQERqn752yLQYGWRhc2hfaDI2NC1iYXNpYy1nZW4yXzcyMHARAHUAZd6oAQA&_nc_gid=4GihSTrCwcBDNmVQ5XOE2Q&_nc_zt=28&oh=00_AfrzH2QdVHoX1wVwx8XJHWvDo3QoWzQY7qsPXMeHDZllrQ&oe=69764BFC"

# Two URLs that should be detected as duplicates (same/similar creative)
DUPLICATE_URL_1 = \
"https://scontent.fper13-1.fna.fbcdn.net/v/t39.35426-6/597642536_1403055954549420_1685776912614701854_n.jpg?stp=dst-jpg_s600x600_tt6&_nc_cat=110&ccb=1-7&_nc_sid=c53f8f&_nc_ohc=zZ-zwJXDDZoQ7kNvwGYwDTw&_nc_oc=AdnBdY8twjZ8oEuvKqTN0Z8NdXSHXXVK-ApG4qMNcaH2Hm1_MRXbE67CJ3YIdOv0p8Q&_nc_zt=14&_nc_ht=scontent.fper13-1.fna&_nc_gid=cnCRDfRBljdpLMl9Xa45Qg&oh=00_AfrmpsX3OvY1Xcg8ihdvrCSjvAIkoPZiQQ4RgAkj7sannw&oe=69763A6E"
DUPLICATE_URL_2 = \
    "https://scontent.fper13-1.fna.fbcdn.net/v/t39.35426-6/597930350_1779530402764258_7507426393546707764_n.jpg?stp=dst-jpg_s600x600_tt6&_nc_cat=111&ccb=1-7&_nc_sid=c53f8f&_nc_ohc=W4YpBwQENOAQ7kNvwEuydVh&_nc_oc=AdkmjxPvETzFwQFEWof35ZV59jBS3LZdX2US4oeJZJa84ClHoIxH_LrkwwqcQGwHSKE&_nc_zt=14&_nc_ht=scontent.fper13-1.fna&_nc_gid=dnGr5bognAdHj7ikRebaXA&oh=00_AfrU1sfEmM2nZ7vnT_VketURCCkMW3-hgO58Oo4p8npuhg&oe=69764F18"
# A URL that should NOT match the duplicates above
UNIQUE_URL = "https://video.xx.fbcdn.net/o1/v/t2/f2/m366/AQODqkIhM0tq2FBzdbdW1kMHTLxFwy2A6KGctyYC5kt72C1AJu1c-JB2wM8P9WlVu3yhJKgiN-U8J2HMWgGTckL9LEVCxnY_b7p5FQJeT-pqxA.mp4?_nc_cat=100&_nc_oc=AdkGf2Hdn9eSTLw2wFQdwqqp3AGHzuA-DumtDda_hgOCGrrLjHdmNZNL77xq8fB0DzY&_nc_sid=5e9851&_nc_ht=video.fper13-1.fna.fbcdn.net&_nc_ohc=z6ukyBv4D8AQ7kNvwF1-sBq&efg=eyJ2ZW5jb2RlX3RhZyI6Inhwdl9wcm9ncmVzc2l2ZS5WSV9VU0VDQVNFX1BST0RVQ1RfVFlQRS4uQzMuNzIwLmRhc2hfaDI2NC1iYXNpYy1nZW4yXzcyMHAiLCJ4cHZfYXNzZXRfaWQiOjQyMDA2ODc0NzY4NzA1ODEsImFzc2V0X2FnZV9kYXlzIjozNCwidmlfdXNlY2FzZV9pZCI6MTA3OTksImR1cmF0aW9uX3MiOjQwLCJ1cmxnZW5fc291cmNlIjoid3d3In0%3D&ccb=17-1&vs=33af0fb628b2b574&_nc_vs=HBksFQIYRWZiX2VwaGVtZXJhbC9GMzRGOUU5MkU3NzM3QTA0ODFBRjA4QjZGNzY5RUI4RV9tdF8xX3ZpZGVvX2Rhc2hpbml0Lm1wNBUAAsgBEgAVAhhAZmJfcGVybWFuZW50LzIyNDg4QUFCOUY1MEYzNzVDOTIzNDIzNzFEMTUzMEI5X2F1ZGlvX2Rhc2hpbml0Lm1wNBUCAsgBEgAoABgAGwKIB3VzZV9vaWwBMRJwcm9ncmVzc2l2ZV9yZWNpcGUBMRUAACbqtvjNmKD2DhUCKAJDMywXQERqn752yLQYGWRhc2hfaDI2NC1iYXNpYy1nZW4yXzcyMHARAHUAZd6oAQA&_nc_gid=4GihSTrCwcBDNmVQ5XOE2Q&_nc_zt=28&oh=00_AfrzH2QdVHoX1wVwx8XJHWvDo3QoWzQY7qsPXMeHDZllrQ&oe=69764BFC"


@pytest.fixture
def detector():
    """Create a DuplicateDetector instance."""
    return DuplicateDetector()


class TestDuplicateDetectionWithUrls:
    """Tests for duplicate detection using creative URLs directly (no DB required)."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not DUPLICATE_URL_1 or not DUPLICATE_URL_2, reason="No test URLs configured")
    async def test_duplicate_urls_detected(self, detector: DuplicateDetector):
        """Test that known duplicate URLs are correctly identified."""
        hash1 = await detector.get_phash_from_url(DUPLICATE_URL_1, creative_type="video")
        hash2 = await detector.get_phash_from_url(DUPLICATE_URL_2, creative_type="video")

        assert hash1 is not None, f"Could not compute hash for {DUPLICATE_URL_1}"
        assert hash2 is not None, f"Could not compute hash for {DUPLICATE_URL_2}"

        distance = detector.hamming_distance(hash1, hash2)
        print(f"Hamming distance between duplicate URLs: {distance}")

        assert detector.are_hashes_duplicate(hash1, hash2), (
            f"Known duplicate URLs not detected as duplicates. Distance: {distance}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(not UNIQUE_URL or not DUPLICATE_URL_1, reason="No test URLs configured")
    async def test_unique_url_not_duplicate(self, detector: DuplicateDetector):
        """Test that a unique URL is not flagged as duplicate."""
        unique_hash = await detector.get_phash_from_url(UNIQUE_URL, creative_type="video")
        dup_hash = await detector.get_phash_from_url(DUPLICATE_URL_1, creative_type="video")

        assert unique_hash is not None, f"Could not compute hash for {UNIQUE_URL}"
        assert dup_hash is not None, f"Could not compute hash for {DUPLICATE_URL_1}"

        is_dup = detector.are_hashes_duplicate(unique_hash, dup_hash)
        assert is_dup is False, "Unique URL incorrectly flagged as duplicate"


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


# class TestMediaIdExtraction:
#     """Tests for Meta CDN media ID extraction."""

#     def test_extract_media_id_from_standard_url(self, detector: DuplicateDetector):
#         """Test extraction from standard Meta CDN URL."""
#         url = "https://scontent.xx.fbcdn.net/v/t39.30808-6/456789123_something.jpg"
#         media_id = detector.extract_media_id_from_url(url)
#         assert media_id == "456789123"

#     def test_extract_media_id_from_url_with_extension(self, detector: DuplicateDetector):
#         """Test extraction when ID is followed by extension."""
#         url = "https://scontent.xx.fbcdn.net/v/t39.30808-6/123456789012.jpg"
#         media_id = detector.extract_media_id_from_url(url)
#         assert media_id == "123456789012"

#     def test_extract_media_id_returns_none_for_invalid_url(self, detector: DuplicateDetector):
#         """Test that invalid URLs return None."""
#         url = "https://example.com/image.jpg"
#         media_id = detector.extract_media_id_from_url(url)
#         assert media_id is None

#     def test_extract_media_id_returns_none_for_empty_url(self, detector: DuplicateDetector):
#         """Test that empty/None URLs return None."""
#         assert detector.extract_media_id_from_url("") is None
#         assert detector.extract_media_id_from_url(None) is None
