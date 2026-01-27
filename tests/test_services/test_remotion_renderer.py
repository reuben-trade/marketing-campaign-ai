"""Tests for Remotion renderer service."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rendered_video import RenderedVideo
from app.schemas.remotion_payload import (
    AudioTrack,
    BrandProfile,
    CompositionType,
    RemotionPayload,
    SegmentType,
    TimelineSegment,
    VideoClipSource,
)
from app.schemas.render import RenderStatus
from app.services.remotion_renderer import RemotionRendererService


@pytest.fixture
def sample_payload() -> RemotionPayload:
    """Create a sample Remotion payload for testing."""
    return RemotionPayload(
        composition_id=CompositionType.VERTICAL,
        width=1080,
        height=1920,
        fps=30,
        duration_in_frames=900,
        project_id=uuid.uuid4(),
        timeline=[
            TimelineSegment(
                id="segment_01",
                type=SegmentType.VIDEO_CLIP,
                start_frame=0,
                duration_frames=300,
                source=VideoClipSource(
                    url="https://example.com/video.mp4",
                    start_time=0.0,
                    end_time=10.0,
                ),
            ),
            TimelineSegment(
                id="segment_02",
                type=SegmentType.TEXT_SLIDE,
                start_frame=300,
                duration_frames=150,
                text_content={
                    "headline": "Test Headline",
                    "subheadline": "Test Subheadline",
                },
            ),
        ],
        brand_profile=BrandProfile(
            primary_color="#FF5733",
            font_family="Inter",
        ),
        audio_track=AudioTrack(
            url="https://example.com/audio.mp3",
            volume=0.8,
        ),
    )


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_storage():
    """Create a mock storage client."""
    storage = MagicMock()
    storage.upload_file = MagicMock(return_value="https://storage.example.com/video.mp4")
    storage.delete_file = MagicMock()
    return storage


class TestRemotionRendererService:
    """Tests for RemotionRendererService."""

    @pytest.mark.asyncio
    async def test_create_render_job(
        self,
        mock_db: MagicMock,
        sample_payload: RemotionPayload,
    ):
        """Test creating a new render job."""
        service = RemotionRendererService(mock_db)
        project_id = uuid.uuid4()

        # Mock the database behavior
        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.utcnow()

        mock_db.refresh = mock_refresh

        render = await service.create_render_job(project_id, sample_payload)

        assert render.project_id == project_id
        assert render.status == RenderStatus.PENDING.value
        assert render.composition_id == CompositionType.VERTICAL.value
        assert render.remotion_payload is not None
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_render(self, mock_db: MagicMock):
        """Test getting a render by ID."""
        render_id = uuid.uuid4()
        mock_render = RenderedVideo(
            id=render_id,
            project_id=uuid.uuid4(),
            status=RenderStatus.PENDING.value,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_render
        mock_db.execute.return_value = mock_result

        service = RemotionRendererService(mock_db)
        result = await service.get_render(render_id)

        assert result == mock_render

    @pytest.mark.asyncio
    async def test_get_render_not_found(self, mock_db: MagicMock):
        """Test getting a non-existent render."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = RemotionRendererService(mock_db)
        result = await service.get_render(uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_update_payload(
        self,
        mock_db: MagicMock,
        sample_payload: RemotionPayload,
    ):
        """Test updating a render payload."""
        render_id = uuid.uuid4()
        mock_render = RenderedVideo(
            id=render_id,
            project_id=uuid.uuid4(),
            status=RenderStatus.PENDING.value,
            remotion_payload={},
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_render
        mock_db.execute.return_value = mock_result

        service = RemotionRendererService(mock_db)
        result = await service.update_payload(render_id, sample_payload)

        assert result is not None
        assert result.composition_id == CompositionType.VERTICAL.value

    @pytest.mark.asyncio
    async def test_update_payload_wrong_status(
        self,
        mock_db: MagicMock,
        sample_payload: RemotionPayload,
    ):
        """Test that updating payload fails for non-pending renders."""
        render_id = uuid.uuid4()
        mock_render = RenderedVideo(
            id=render_id,
            project_id=uuid.uuid4(),
            status=RenderStatus.RENDERING.value,
            remotion_payload={},
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_render
        mock_db.execute.return_value = mock_result

        service = RemotionRendererService(mock_db)

        with pytest.raises(ValueError, match="Cannot update payload"):
            await service.update_payload(render_id, sample_payload)

    @pytest.mark.asyncio
    async def test_cancel_render(self, mock_db: MagicMock):
        """Test cancelling a render."""
        render_id = uuid.uuid4()
        mock_render = RenderedVideo(
            id=render_id,
            project_id=uuid.uuid4(),
            status=RenderStatus.PENDING.value,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_render
        mock_db.execute.return_value = mock_result

        service = RemotionRendererService(mock_db)
        result = await service.cancel_render(render_id)

        assert result is not None
        assert result.status == RenderStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_cancel_completed_render_fails(self, mock_db: MagicMock):
        """Test that cancelling a completed render fails."""
        render_id = uuid.uuid4()
        mock_render = RenderedVideo(
            id=render_id,
            project_id=uuid.uuid4(),
            status=RenderStatus.COMPLETED.value,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_render
        mock_db.execute.return_value = mock_result

        service = RemotionRendererService(mock_db)

        with pytest.raises(ValueError, match="Cannot cancel completed render"):
            await service.cancel_render(render_id)

    @pytest.mark.asyncio
    async def test_delete_render(self, mock_db: MagicMock, mock_storage: MagicMock):
        """Test deleting a render."""
        render_id = uuid.uuid4()
        project_id = uuid.uuid4()
        mock_render = RenderedVideo(
            id=render_id,
            project_id=project_id,
            status=RenderStatus.COMPLETED.value,
            video_url="https://example.com/video.mp4",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_render
        mock_db.execute.return_value = mock_result

        service = RemotionRendererService(mock_db)
        service.storage = mock_storage

        result = await service.delete_render(render_id)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_render)

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, mock_db: MagicMock):
        """Test getting render queue statistics."""
        # Mock count queries
        mock_counts = [5, 2, 10, 3]  # pending, rendering, completed_today, failed_today
        mock_avg = 45.5

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            result = MagicMock()
            if call_count < 4:
                result.scalar.return_value = mock_counts[call_count]
            else:
                result.scalar.return_value = mock_avg
            call_count += 1
            return result

        mock_db.execute = mock_execute

        service = RemotionRendererService(mock_db)
        stats = await service.get_queue_stats()

        assert stats["pending_count"] == 5
        assert stats["rendering_count"] == 2
        assert stats["completed_today"] == 10
        assert stats["failed_today"] == 3


class TestRemotionLambdaRendering:
    """Tests for Lambda rendering functionality."""

    @pytest.mark.asyncio
    async def test_build_lambda_input(
        self,
        mock_db: MagicMock,
        sample_payload: RemotionPayload,
    ):
        """Test building Lambda input payload."""
        service = RemotionRendererService(mock_db)

        render = RenderedVideo(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            status=RenderStatus.PENDING.value,
            remotion_payload=sample_payload.model_dump(mode="json"),
        )

        mock_settings = MagicMock()
        mock_settings.remotion_serve_url = "https://example.s3.amazonaws.com/index.html"
        mock_settings.remotion_aws_region = "us-east-1"
        mock_settings.remotion_site_name = "test-site"

        lambda_input = service._build_lambda_input(render, sample_payload, mock_settings)

        assert lambda_input["type"] == "start"
        assert lambda_input["serveUrl"] == "https://example.s3.amazonaws.com/index.html"
        assert lambda_input["composition"] == "vertical_ad_v1"
        assert lambda_input["codec"] == "h264"
        assert "inputProps" in lambda_input

    @pytest.mark.asyncio
    async def test_render_lambda_not_configured(self, mock_db: MagicMock):
        """Test that Lambda rendering fails when not configured."""
        render = RenderedVideo(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            status=RenderStatus.PENDING.value,
            remotion_payload={},
        )

        service = RemotionRendererService(mock_db)

        with patch("app.services.remotion_renderer.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.remotion_lambda_enabled = False
            mock_get_settings.return_value = mock_settings

            with pytest.raises(ValueError, match="Remotion Lambda not configured"):
                await service._render_lambda(render)

    @pytest.mark.asyncio
    async def test_render_lambda_success(
        self,
        mock_db: MagicMock,
        sample_payload: RemotionPayload,
    ):
        """Test successful Lambda rendering."""
        render = RenderedVideo(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            status=RenderStatus.RENDERING.value,
            remotion_payload=sample_payload.model_dump(mode="json"),
        )

        service = RemotionRendererService(mock_db)

        with patch("app.services.remotion_renderer.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.remotion_lambda_enabled = True
            mock_settings.remotion_aws_region = "us-east-1"
            mock_settings.remotion_function_name = "remotion-render-test"
            mock_settings.remotion_site_name = "test-site"
            mock_settings.remotion_serve_url = ""
            mock_settings.aws_access_key_id = ""
            mock_settings.aws_secret_access_key = ""
            mock_get_settings.return_value = mock_settings

            # Mock the Lambda invocation
            mock_lambda_result = {
                "outputUrl": "https://s3.amazonaws.com/output.mp4",
                "fileSizeBytes": 1000000,
            }

            with patch.object(
                service,
                "_invoke_lambda_render",
                new_callable=AsyncMock,
            ) as mock_invoke:
                mock_invoke.return_value = mock_lambda_result

                with patch.object(
                    service,
                    "_transfer_lambda_output",
                    new_callable=AsyncMock,
                ) as mock_transfer:
                    mock_transfer.return_value = "https://supabase.example.com/video.mp4"

                    result = await service._render_lambda(render)

                    assert result["video_url"] == "https://supabase.example.com/video.mp4"
                    assert result["file_size_bytes"] == 1000000
                    assert "duration_seconds" in result
                    assert "render_time_seconds" in result

    @pytest.mark.asyncio
    async def test_start_render_auto_mode_lambda(
        self,
        mock_db: MagicMock,
        sample_payload: RemotionPayload,
    ):
        """Test that start_render auto-selects Lambda when configured."""
        render_id = uuid.uuid4()
        render = RenderedVideo(
            id=render_id,
            project_id=uuid.uuid4(),
            status=RenderStatus.PENDING.value,
            remotion_payload=sample_payload.model_dump(mode="json"),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = render
        mock_db.execute.return_value = mock_result

        service = RemotionRendererService(mock_db)

        with patch("app.services.remotion_renderer.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.remotion_lambda_enabled = True
            mock_settings.remotion_aws_region = "us-east-1"
            mock_settings.remotion_function_name = "remotion-render-test"
            mock_settings.remotion_site_name = "test-site"
            mock_settings.remotion_serve_url = ""
            mock_settings.aws_access_key_id = ""
            mock_settings.aws_secret_access_key = ""
            mock_get_settings.return_value = mock_settings

            with patch.object(
                service,
                "_render_lambda",
                new_callable=AsyncMock,
            ) as mock_lambda:
                mock_lambda.return_value = {
                    "video_url": "https://example.com/video.mp4",
                    "thumbnail_url": None,
                    "duration_seconds": 30.0,
                    "file_size_bytes": 1000000,
                    "render_time_seconds": 45.0,
                }

                result = await service.start_render(render_id, mode=None)

                mock_lambda.assert_called_once()
                assert result.status == RenderStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_start_render_auto_mode_local(
        self,
        mock_db: MagicMock,
        sample_payload: RemotionPayload,
    ):
        """Test that start_render auto-selects local when Lambda not configured."""
        render_id = uuid.uuid4()
        render = RenderedVideo(
            id=render_id,
            project_id=uuid.uuid4(),
            status=RenderStatus.PENDING.value,
            remotion_payload=sample_payload.model_dump(mode="json"),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = render
        mock_db.execute.return_value = mock_result

        service = RemotionRendererService(mock_db)

        with patch("app.services.remotion_renderer.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.remotion_lambda_enabled = False
            mock_get_settings.return_value = mock_settings

            with patch.object(
                service,
                "_render_local",
                new_callable=AsyncMock,
            ) as mock_local:
                mock_local.return_value = {
                    "video_url": "https://example.com/video.mp4",
                    "thumbnail_url": None,
                    "duration_seconds": 30.0,
                    "file_size_bytes": 1000000,
                    "render_time_seconds": 45.0,
                }

                result = await service.start_render(render_id, mode=None)

                mock_local.assert_called_once()
                assert result.status == RenderStatus.COMPLETED.value


class TestTransferLambdaOutput:
    """Tests for Lambda output transfer."""

    @pytest.mark.asyncio
    async def test_transfer_lambda_output(self, mock_db: MagicMock, mock_storage: MagicMock):
        """Test transferring Lambda output to Supabase."""
        service = RemotionRendererService(mock_db)
        service.storage = mock_storage

        lambda_url = "https://s3.amazonaws.com/bucket/output.mp4"
        project_id = uuid.uuid4()
        render_id = uuid.uuid4()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = b"video content"
            mock_response.raise_for_status = MagicMock()

            async def mock_get(*args, **kwargs):
                return mock_response

            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service._transfer_lambda_output(lambda_url, project_id, render_id)

            assert result == "https://storage.example.com/video.mp4"
            mock_storage.upload_file.assert_called_once()
