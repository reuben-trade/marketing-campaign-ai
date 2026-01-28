"""Tests for reference ad upload and fetch API endpoints."""

import uuid
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor
from app.schemas.recipe import ReferenceAdResponse


@pytest.fixture
def mock_video_content() -> bytes:
    """Create mock video content."""
    return b"mock video content" * 1000


class TestUploadReferenceAd:
    """Tests for POST /api/recipes/upload-reference endpoint."""

    @pytest.mark.asyncio
    async def test_upload_reference_ad_success(
        self,
        client,
        db_session: AsyncSession,
        mock_video_content: bytes,
    ):
        """Test successful reference ad upload."""
        with patch(
            "app.services.reference_ad_service.ReferenceAdService.upload_reference_ad"
        ) as mock_upload:
            mock_upload.return_value = ReferenceAdResponse(
                ad_id=uuid.uuid4(),
                recipe=None,
                status="success",
                message="Reference ad processed",
                processing_notes=["Uploaded to storage"],
            )

            response = client.post(
                "/api/recipes/upload-reference",
                files={"file": ("test.mp4", BytesIO(mock_video_content), "video/mp4")},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "success"
            assert "ad_id" in data

    @pytest.mark.asyncio
    async def test_upload_reference_ad_invalid_type(self, client):
        """Test upload with invalid file type."""
        response = client.post(
            "/api/recipes/upload-reference",
            files={"file": ("test.txt", BytesIO(b"text content"), "text/plain")},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_reference_ad_empty_file(self, client):
        """Test upload with empty file."""
        response = client.post(
            "/api/recipes/upload-reference",
            files={"file": ("test.mp4", BytesIO(b""), "video/mp4")},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Empty file" in response.json()["detail"]


class TestFetchReferenceAdFromUrl:
    """Tests for POST /api/recipes/fetch-url endpoint."""

    @pytest.mark.asyncio
    async def test_fetch_reference_ad_success(self, client, db_session: AsyncSession):
        """Test successful reference ad fetch from URL."""
        with patch(
            "app.services.reference_ad_service.ReferenceAdService.fetch_from_url"
        ) as mock_fetch:
            mock_fetch.return_value = ReferenceAdResponse(
                ad_id=uuid.uuid4(),
                recipe=None,
                status="success",
                message="Reference ad fetched",
                processing_notes=["Downloaded from URL"],
            )

            response = client.post(
                "/api/recipes/fetch-url",
                json={"url": "https://example.com/video.mp4"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "success"
            assert "ad_id" in data

    @pytest.mark.asyncio
    async def test_fetch_reference_ad_with_custom_name(self, client, db_session: AsyncSession):
        """Test fetch with custom recipe name."""
        with patch(
            "app.services.reference_ad_service.ReferenceAdService.fetch_from_url"
        ) as mock_fetch:
            mock_fetch.return_value = ReferenceAdResponse(
                ad_id=uuid.uuid4(),
                recipe=None,
                status="success",
                message="Reference ad fetched",
                processing_notes=[],
            )

            response = client.post(
                "/api/recipes/fetch-url",
                json={"url": "https://example.com/video.mp4", "name": "My Custom Recipe"},
            )

            assert response.status_code == status.HTTP_200_OK
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args
            assert call_args.kwargs["custom_name"] == "My Custom Recipe"


class TestReferenceAdService:
    """Tests for ReferenceAdService."""

    @pytest.mark.asyncio
    async def test_ensure_reference_competitor_creates_new(self, db_session: AsyncSession):
        """Test that reference competitor is created if it doesn't exist."""
        from app.services.reference_ad_service import (
            REFERENCE_ADS_PAGE_ID,
            ReferenceAdService,
        )

        service = ReferenceAdService()
        competitor = await service._ensure_reference_competitor(db_session)

        assert competitor is not None
        assert competitor.page_id == REFERENCE_ADS_PAGE_ID
        assert competitor.company_name == "Reference Ads"

    @pytest.mark.asyncio
    async def test_ensure_reference_competitor_reuses_existing(self, db_session: AsyncSession):
        """Test that existing reference competitor is reused."""
        from app.services.reference_ad_service import (
            REFERENCE_ADS_COMPETITOR_ID,
            REFERENCE_ADS_PAGE_ID,
            ReferenceAdService,
        )

        # Create competitor first
        existing = Competitor(
            id=REFERENCE_ADS_COMPETITOR_ID,
            company_name="Reference Ads",
            page_id=REFERENCE_ADS_PAGE_ID,
            industry="Reference",
        )
        db_session.add(existing)
        await db_session.commit()

        service = ReferenceAdService()
        competitor = await service._ensure_reference_competitor(db_session)

        assert competitor.id == REFERENCE_ADS_COMPETITOR_ID

    def test_get_mime_type(self):
        """Test MIME type detection from filename."""
        from app.services.reference_ad_service import ReferenceAdService

        service = ReferenceAdService()

        assert service._get_mime_type("video.mp4") == "video/mp4"
        assert service._get_mime_type("video.webm") == "video/webm"
        assert service._get_mime_type("video.mov") == "video/quicktime"
        assert service._get_mime_type("video.unknown") == "video/mp4"
