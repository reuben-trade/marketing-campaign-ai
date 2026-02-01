"""Tests for content analysis Celery tasks."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import nest_asyncio
import pytest

from app.models.project import Project
from app.models.project_file import ProjectFile

# Allow nested event loops for testing Celery tasks that use asyncio.run()
nest_asyncio.apply()


@pytest.fixture
def sample_gemini_response():
    """Sample response from Gemini video analysis."""
    return {
        "video_level_summary": "A product demonstration video.",
        "video_level_tags": ["product", "demo"],
        "total_duration_seconds": 15.0,
        "dominant_theme": "product showcase",
        "production_style": "professional",
        "content_type": "demo",
        "srt_subtitles": "1\n00:00:01,000 --> 00:00:03,000\nThis is a test\n",
        "segments": [
            {
                "timestamp_start": 0.0,
                "timestamp_end": 5.0,
                "visual_description": "Close-up of product",
                "action_tags": ["product", "close-up"],
                "scene_type": "product_demo",
                "has_text_overlay": False,
                "has_face": False,
                "has_product": True,
                "has_speech": False,
                "section_type": "product_display",
                "section_label": "Product showcase",
                "attention_score": 8,
                "emotion_intensity": 6,
            },
            {
                "timestamp_start": 5.0,
                "timestamp_end": 10.0,
                "visual_description": "Person speaking",
                "action_tags": ["talking", "testimonial"],
                "scene_type": "testimonial",
                "has_text_overlay": False,
                "has_face": True,
                "has_product": False,
                "has_speech": True,
                "section_type": "testimonial",
                "section_label": "Customer review",
                "attention_score": 7,
                "emotion_intensity": 8,
            },
        ],
    }


@pytest.fixture
def mock_gemini_client(sample_gemini_response):
    """Mock Gemini client."""
    mock_client = MagicMock()

    # Mock file upload
    mock_file = MagicMock()
    mock_file.name = "test-file-id"
    mock_file.state = MagicMock()
    mock_file.state.name = "ACTIVE"
    mock_client.files.upload.return_value = mock_file
    mock_client.files.get.return_value = mock_file
    mock_client.files.delete.return_value = None

    # Mock content generation
    mock_response = MagicMock()
    mock_response.text = json.dumps(sample_gemini_response)
    mock_client.models.generate_content.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for embeddings."""
    mock_service = MagicMock()
    mock_service.generate_embedding = AsyncMock(return_value=[0.01] * 1536)
    return mock_service


@pytest.fixture
def mock_storage():
    """Mock Supabase storage."""
    mock = MagicMock()
    mock.download_file = AsyncMock(return_value=b"fake video content")
    return mock


class TestAnalyzeProjectFileTask:
    """Tests for analyze_project_file_task."""

    @pytest.mark.asyncio
    async def test_analyze_file_success(
        self,
        db_session,
        mock_gemini_client,
        mock_embedding_service,
        mock_storage,
    ):
        """Test successful file analysis via task."""
        # Create test project and file
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
            status=Project.STATUS_DRAFT,
        )
        db_session.add(project)

        project_file = ProjectFile(
            id=uuid.uuid4(),
            project_id=project.id,
            filename="test.mp4",
            original_filename="Test Video.mp4",
            storage_path="user-uploads/test.mp4",
            file_url="https://storage.example.com/test.mp4",
            file_size_bytes=1000000,
            content_type="video/mp4",
            status=ProjectFile.STATUS_PENDING,
        )
        db_session.add(project_file)
        await db_session.commit()

        file_id = str(project_file.id)

        # Import and run task
        with (
            patch("app.tasks.content_analysis_tasks.get_async_session") as mock_get_session,
            patch("app.services.user_content_analyzer.genai.Client") as mock_genai,
            patch("app.services.user_content_analyzer.EmbeddingService") as mock_emb_class,
            patch("app.services.user_content_analyzer.SupabaseStorage") as mock_storage_class,
        ):
            # Set up the async session mock to use our test db_session
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            mock_genai.return_value = mock_gemini_client
            mock_emb_class.return_value = mock_embedding_service
            mock_storage_class.return_value = mock_storage

            from app.tasks.content_analysis_tasks import analyze_project_file_task

            # Run the task synchronously (simulates Celery worker)
            result = analyze_project_file_task(file_id)

            assert result["status"] == "completed"
            assert result["file_id"] == file_id
            assert result["segments_created"] == 2

    @pytest.mark.asyncio
    async def test_analyze_file_not_found(self, db_session):
        """Test task when file doesn't exist."""
        fake_id = str(uuid.uuid4())

        with patch("app.tasks.content_analysis_tasks.get_async_session") as mock_get_session:
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            from app.tasks.content_analysis_tasks import analyze_project_file_task

            result = analyze_project_file_task(fake_id)

            assert result["status"] == "error"
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_analyze_file_already_completed(self, db_session):
        """Test task skips already completed files."""
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
            status=Project.STATUS_DRAFT,
        )
        db_session.add(project)

        project_file = ProjectFile(
            id=uuid.uuid4(),
            project_id=project.id,
            filename="test.mp4",
            original_filename="Test.mp4",
            storage_path="user-uploads/test.mp4",
            file_size_bytes=1000000,
            content_type="video/mp4",
            status=ProjectFile.STATUS_COMPLETED,  # Already done
        )
        db_session.add(project_file)
        await db_session.commit()

        file_id = str(project_file.id)

        with patch("app.tasks.content_analysis_tasks.get_async_session") as mock_get_session:
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            from app.tasks.content_analysis_tasks import analyze_project_file_task

            result = analyze_project_file_task(file_id)

            assert result["status"] == "skipped"
            assert result["reason"] == "Already completed"


class TestAnalyzePendingFilesTask:
    """Tests for analyze_pending_files_task."""

    @pytest.mark.asyncio
    async def test_queues_pending_files(self, db_session):
        """Test that pending files get queued for analysis."""
        # Create project and pending files
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
        )
        db_session.add(project)

        pending_files = []
        for i in range(3):
            pf = ProjectFile(
                id=uuid.uuid4(),
                project_id=project.id,
                filename=f"video_{i}.mp4",
                original_filename=f"Video {i}.mp4",
                storage_path=f"user-uploads/video_{i}.mp4",
                file_size_bytes=1000000,
                content_type="video/mp4",
                status=ProjectFile.STATUS_PENDING,
            )
            db_session.add(pf)
            pending_files.append(pf)

        await db_session.commit()

        with (
            patch("app.tasks.content_analysis_tasks.get_sync_session") as mock_get_session,
            patch("app.tasks.content_analysis_tasks.analyze_project_file_task") as mock_task,
        ):
            # Create a mock session that returns our pending files
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = pending_files
            mock_session.query.return_value = mock_query
            mock_session.close = MagicMock()
            mock_get_session.return_value = mock_session

            mock_task.delay = MagicMock()

            from app.tasks.content_analysis_tasks import analyze_pending_files_task

            result = analyze_pending_files_task(batch_size=10)

            assert result["status"] == "completed"
            assert result["queued"] == 3
            assert mock_task.delay.call_count == 3


class TestRetryFailedAnalysisTask:
    """Tests for retry_failed_analysis_task."""

    @pytest.mark.asyncio
    async def test_retries_failed_files(self, db_session):
        """Test that failed files get reset and requeued."""
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
        )
        db_session.add(project)

        failed_files = []
        for i in range(2):
            pf = ProjectFile(
                id=uuid.uuid4(),
                project_id=project.id,
                filename=f"failed_{i}.mp4",
                original_filename=f"Failed {i}.mp4",
                storage_path=f"user-uploads/failed_{i}.mp4",
                file_size_bytes=1000000,
                content_type="video/mp4",
                status=ProjectFile.STATUS_FAILED,
            )
            db_session.add(pf)
            failed_files.append(pf)

        await db_session.commit()

        with (
            patch("app.tasks.content_analysis_tasks.get_sync_session") as mock_get_session,
            patch("app.tasks.content_analysis_tasks.analyze_project_file_task") as mock_task,
        ):
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.all.return_value = failed_files
            mock_session.query.return_value = mock_query
            mock_session.commit = MagicMock()
            mock_session.close = MagicMock()
            mock_get_session.return_value = mock_session

            mock_task.delay = MagicMock()

            from app.tasks.content_analysis_tasks import retry_failed_analysis_task

            result = retry_failed_analysis_task()

            assert result["status"] == "completed"
            assert result["queued"] == 2
            assert mock_task.delay.call_count == 2

            # Verify status was reset to pending
            for pf in failed_files:
                assert pf.status == ProjectFile.STATUS_PENDING


class TestCeleryAppConfiguration:
    """Tests for Celery app configuration."""

    def test_content_analysis_tasks_registered(self):
        """Test that content_analysis_tasks is in the include list."""
        from app.tasks.celery_app import celery_app

        assert "app.tasks.content_analysis_tasks" in celery_app.conf.include

    def test_content_analysis_queue_exists(self):
        """Test that content_analysis queue is configured."""
        from app.tasks.celery_app import celery_app

        assert "content_analysis" in celery_app.conf.task_queues

    def test_content_analysis_route_configured(self):
        """Test that content analysis tasks route to correct queue."""
        from app.tasks.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert "app.tasks.content_analysis_tasks.*" in routes
        assert routes["app.tasks.content_analysis_tasks.*"]["queue"] == "content_analysis"
