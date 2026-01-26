"""Tests for user content analyzer service."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user_video_segment import UserVideoSegment
from app.schemas.user_video_segment import SegmentAnalysis, VideoAnalysisResult
from app.services.user_content_analyzer import (
    USER_CONTENT_ANALYSIS_PROMPT,
    UserContentAnalyzer,
    UserContentAnalyzerError,
)


@pytest.fixture
def sample_gemini_response():
    """Sample response from Gemini video analysis."""
    return {
        "video_level_summary": "A product demonstration video showing a smartphone from multiple angles with a presenter explaining features.",
        "video_level_tags": ["smartphone", "tech", "product-demo", "unboxing"],
        "total_duration_seconds": 30.0,
        "dominant_theme": "product showcase",
        "production_style": "professional",
        "content_type": "demo",
        "segments": [
            {
                "timestamp_start": 0.0,
                "timestamp_end": 3.5,
                "visual_description": "Close-up of hands holding a sleek silver smartphone, tilting it to show the camera module. Soft natural lighting, white background.",
                "action_tags": ["hands", "smartphone", "product-reveal", "close-up", "tech"],
                "scene_type": "product_demo",
                "emotion": "curiosity",
                "camera_shot": "close-up",
                "motion_type": "handheld",
                "has_text_overlay": False,
                "has_face": False,
                "has_product": True,
            },
            {
                "timestamp_start": 3.5,
                "timestamp_end": 8.0,
                "visual_description": "Young woman in her 20s smiling at camera in a modern office. Speaking enthusiastically with hand gestures. Ring light visible in eye reflection.",
                "action_tags": ["testimonial", "female", "office", "speaking", "enthusiastic"],
                "scene_type": "testimonial",
                "emotion": "excitement",
                "camera_shot": "medium",
                "motion_type": "static",
                "has_text_overlay": False,
                "has_face": True,
                "has_product": False,
            },
            {
                "timestamp_start": 8.0,
                "timestamp_end": 15.0,
                "visual_description": "Split screen showing before/after comparison. Left side shows old phone with cracked screen, right shows new phone with pristine display.",
                "action_tags": ["before-after", "comparison", "smartphone", "upgrade"],
                "scene_type": "before_after",
                "emotion": "trust",
                "camera_shot": "wide",
                "motion_type": "static",
                "has_text_overlay": True,
                "has_face": False,
                "has_product": True,
            },
        ],
    }


@pytest.fixture
def sample_embedding():
    """Sample embedding vector (1536 dimensions)."""
    return [0.01] * 1536


@pytest.fixture
def mock_gemini_client(sample_gemini_response):
    """Mock Gemini client."""
    mock_client = MagicMock()

    # Mock file upload
    mock_file = MagicMock()
    mock_file.name = "test-file-id"
    mock_file.state = MagicMock()
    mock_file.state.name = "ACTIVE"  # Not PROCESSING
    mock_client.files.upload.return_value = mock_file
    mock_client.files.get.return_value = mock_file
    mock_client.files.delete.return_value = None

    # Mock content generation
    mock_response = MagicMock()
    mock_response.text = json.dumps(sample_gemini_response)
    mock_client.models.generate_content.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_embedding_service(sample_embedding):
    """Mock EmbeddingService for embeddings."""
    mock_service = MagicMock()
    mock_service.generate_embedding = AsyncMock(return_value=sample_embedding)
    return mock_service


@pytest.fixture
def mock_storage():
    """Mock Supabase storage."""
    mock = MagicMock()
    mock.download_file = AsyncMock(return_value=b"fake video content")
    return mock


class TestUserContentAnalyzer:
    """Tests for UserContentAnalyzer class."""

    @pytest.mark.asyncio
    async def test_parse_analysis_result(self, sample_gemini_response):
        """Test parsing raw Gemini response into VideoAnalysisResult."""
        analyzer = UserContentAnalyzer.__new__(UserContentAnalyzer)

        result = analyzer._parse_analysis_result(sample_gemini_response)

        assert isinstance(result, VideoAnalysisResult)
        assert result.video_level_summary == sample_gemini_response["video_level_summary"]
        assert result.total_duration_seconds == 30.0
        assert len(result.segments) == 3

        # Check first segment
        seg1 = result.segments[0]
        assert seg1.timestamp_start == 0.0
        assert seg1.timestamp_end == 3.5
        assert "smartphone" in seg1.visual_description.lower()
        assert "hands" in seg1.action_tags
        assert seg1.scene_type == "product_demo"
        assert seg1.has_product is True
        assert seg1.has_face is False

    @pytest.mark.asyncio
    async def test_parse_analysis_result_empty_segments(self):
        """Test parsing response with no segments."""
        analyzer = UserContentAnalyzer.__new__(UserContentAnalyzer)

        raw = {
            "video_level_summary": "Empty video",
            "video_level_tags": [],
            "total_duration_seconds": 5.0,
            "segments": [],
        }

        result = analyzer._parse_analysis_result(raw)

        assert len(result.segments) == 0
        assert result.video_level_summary == "Empty video"

    @pytest.mark.asyncio
    async def test_parse_analysis_result_filters_zero_duration(self):
        """Test that segments with zero duration are filtered out."""
        analyzer = UserContentAnalyzer.__new__(UserContentAnalyzer)

        raw = {
            "video_level_summary": "Test",
            "video_level_tags": [],
            "total_duration_seconds": 10.0,
            "segments": [
                {
                    "timestamp_start": 0.0,
                    "timestamp_end": 3.0,
                    "visual_description": "Valid segment",
                    "action_tags": ["valid"],
                },
                {
                    "timestamp_start": 3.0,
                    "timestamp_end": 3.0,  # Zero duration
                    "visual_description": "Invalid segment",
                    "action_tags": ["invalid"],
                },
            ],
        }

        result = analyzer._parse_analysis_result(raw)

        assert len(result.segments) == 1
        assert result.segments[0].visual_description == "Valid segment"

    @pytest.mark.asyncio
    async def test_generate_segment_embedding(self, mock_embedding_service, sample_embedding):
        """Test generating embedding for a segment."""
        with patch("app.services.user_content_analyzer.EmbeddingService") as mock_emb_class, patch(
            "app.services.user_content_analyzer.genai.Client"
        ), patch("app.services.user_content_analyzer.SupabaseStorage"):
            mock_emb_class.return_value = mock_embedding_service

            analyzer = UserContentAnalyzer()
            analyzer.embedding_service = mock_embedding_service

            segment = SegmentAnalysis(
                timestamp_start=0.0,
                timestamp_end=5.0,
                visual_description="Close-up of hands holding smartphone",
                action_tags=["hands", "smartphone", "close-up"],
                scene_type="product_demo",
                emotion="curiosity",
                camera_shot="close-up",
            )

            embedding = await analyzer.generate_segment_embedding(segment)

            assert len(embedding) == 1536
            mock_embedding_service.generate_embedding.assert_called_once()

            # Check the input text includes description and tags
            call_args = mock_embedding_service.generate_embedding.call_args
            input_text = call_args[0][0]
            assert "Close-up of hands" in input_text
            assert "Actions:" in input_text

    @pytest.mark.asyncio
    async def test_analyze_project_file(
        self, db_session, mock_gemini_client, mock_embedding_service, mock_storage, sample_embedding
    ):
        """Test analyzing a single project file."""
        # Create test project
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
            status=Project.STATUS_DRAFT,
        )
        db_session.add(project)

        # Create test project file
        project_file = ProjectFile(
            id=uuid.uuid4(),
            project_id=project.id,
            filename="test_video.mp4",
            original_filename="My Test Video.mp4",
            storage_path="user-uploads/test_video.mp4",
            file_url="https://storage.example.com/test_video.mp4",
            file_size_bytes=1000000,
            content_type="video/mp4",
            status=ProjectFile.STATUS_PENDING,
        )
        db_session.add(project_file)
        await db_session.commit()

        # Set up mocks
        with patch("app.services.user_content_analyzer.genai.Client") as mock_genai, patch(
            "app.services.user_content_analyzer.EmbeddingService"
        ) as mock_emb_class, patch(
            "app.services.user_content_analyzer.SupabaseStorage"
        ) as mock_storage_class:
            mock_genai.return_value = mock_gemini_client
            mock_emb_class.return_value = mock_embedding_service
            mock_storage_class.return_value = mock_storage

            analyzer = UserContentAnalyzer()
            analyzer.gemini_client = mock_gemini_client
            analyzer.embedding_service = mock_embedding_service
            analyzer.storage = mock_storage

            segments = await analyzer.analyze_project_file(db_session, project_file)

            # Verify segments were created
            assert len(segments) == 3

            # Verify segment data
            seg1 = segments[0]
            assert seg1.project_id == project.id
            assert seg1.source_file_id == project_file.id
            assert seg1.source_file_name == "My Test Video.mp4"
            assert seg1.timestamp_start == 0.0
            assert seg1.timestamp_end == 3.5
            assert seg1.embedding is not None

            # Verify file status updated
            await db_session.refresh(project_file)
            assert project_file.status == ProjectFile.STATUS_COMPLETED

    @pytest.mark.asyncio
    async def test_analyze_project_file_failure(self, db_session, mock_gemini_client, mock_storage):
        """Test handling of analysis failure."""
        # Create test project
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
            status=Project.STATUS_DRAFT,
        )
        db_session.add(project)

        # Create test project file
        project_file = ProjectFile(
            id=uuid.uuid4(),
            project_id=project.id,
            filename="test_video.mp4",
            original_filename="My Test Video.mp4",
            storage_path="user-uploads/test_video.mp4",
            file_size_bytes=1000000,
            content_type="video/mp4",
            status=ProjectFile.STATUS_PENDING,
        )
        db_session.add(project_file)
        await db_session.commit()

        # Make download fail
        mock_storage.download_file = AsyncMock(side_effect=Exception("Download failed"))

        with patch("app.services.user_content_analyzer.genai.Client") as mock_genai, patch(
            "app.services.user_content_analyzer.EmbeddingService"
        ), patch("app.services.user_content_analyzer.SupabaseStorage") as mock_storage_class:
            mock_genai.return_value = mock_gemini_client
            mock_storage_class.return_value = mock_storage

            analyzer = UserContentAnalyzer()
            analyzer.storage = mock_storage

            with pytest.raises(UserContentAnalyzerError) as exc_info:
                await analyzer.analyze_project_file(db_session, project_file)

            assert "Download failed" in str(exc_info.value)

            # Verify file status updated to failed
            await db_session.refresh(project_file)
            assert project_file.status == ProjectFile.STATUS_FAILED

    @pytest.mark.asyncio
    async def test_analyze_project(
        self, db_session, mock_gemini_client, mock_embedding_service, mock_storage
    ):
        """Test analyzing all files in a project."""
        # Create test project
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
            status=Project.STATUS_DRAFT,
        )
        db_session.add(project)

        # Create multiple project files
        files = []
        for i in range(2):
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
            files.append(pf)

        await db_session.commit()

        with patch("app.services.user_content_analyzer.genai.Client") as mock_genai, patch(
            "app.services.user_content_analyzer.EmbeddingService"
        ) as mock_emb_class, patch(
            "app.services.user_content_analyzer.SupabaseStorage"
        ) as mock_storage_class:
            mock_genai.return_value = mock_gemini_client
            mock_emb_class.return_value = mock_embedding_service
            mock_storage_class.return_value = mock_storage

            analyzer = UserContentAnalyzer()
            analyzer.gemini_client = mock_gemini_client
            analyzer.embedding_service = mock_embedding_service
            analyzer.storage = mock_storage

            progress = await analyzer.analyze_project(db_session, project.id)

            assert progress.total_files == 2
            assert progress.completed_files == 2
            assert progress.status == "completed"
            # Each video produces 3 segments based on mock
            assert progress.segments_extracted == 6

            # Verify project status updated
            await db_session.refresh(project)
            assert project.status == Project.STATUS_READY

    @pytest.mark.asyncio
    async def test_analyze_project_not_found(self, db_session):
        """Test analyzing non-existent project."""
        with patch("app.services.user_content_analyzer.genai.Client"), patch(
            "app.services.user_content_analyzer.EmbeddingService"
        ), patch("app.services.user_content_analyzer.SupabaseStorage"):
            analyzer = UserContentAnalyzer()

            with pytest.raises(UserContentAnalyzerError) as exc_info:
                await analyzer.analyze_project(db_session, uuid.uuid4())

            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_project_skips_completed_files(
        self, db_session, mock_gemini_client, mock_embedding_service, mock_storage
    ):
        """Test that completed files are skipped by default."""
        # Create test project
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
            status=Project.STATUS_DRAFT,
        )
        db_session.add(project)

        # Create one completed and one pending file
        completed_file = ProjectFile(
            id=uuid.uuid4(),
            project_id=project.id,
            filename="completed.mp4",
            original_filename="Completed.mp4",
            storage_path="user-uploads/completed.mp4",
            file_size_bytes=1000000,
            content_type="video/mp4",
            status=ProjectFile.STATUS_COMPLETED,
        )
        pending_file = ProjectFile(
            id=uuid.uuid4(),
            project_id=project.id,
            filename="pending.mp4",
            original_filename="Pending.mp4",
            storage_path="user-uploads/pending.mp4",
            file_size_bytes=1000000,
            content_type="video/mp4",
            status=ProjectFile.STATUS_PENDING,
        )
        db_session.add(completed_file)
        db_session.add(pending_file)
        await db_session.commit()

        with patch("app.services.user_content_analyzer.genai.Client") as mock_genai, patch(
            "app.services.user_content_analyzer.EmbeddingService"
        ) as mock_emb_class, patch(
            "app.services.user_content_analyzer.SupabaseStorage"
        ) as mock_storage_class:
            mock_genai.return_value = mock_gemini_client
            mock_emb_class.return_value = mock_embedding_service
            mock_storage_class.return_value = mock_storage

            analyzer = UserContentAnalyzer()
            analyzer.gemini_client = mock_gemini_client
            analyzer.embedding_service = mock_embedding_service
            analyzer.storage = mock_storage

            progress = await analyzer.analyze_project(db_session, project.id)

            # Only pending file should be analyzed
            assert progress.total_files == 1
            assert progress.completed_files == 1

    @pytest.mark.asyncio
    async def test_get_project_segments(self, db_session):
        """Test getting all segments for a project."""
        # Create test project
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
        )
        db_session.add(project)

        # Create some segments
        file_id = uuid.uuid4()
        for i in range(3):
            segment = UserVideoSegment(
                project_id=project.id,
                source_file_id=file_id,
                source_file_name="test.mp4",
                timestamp_start=float(i * 5),
                timestamp_end=float((i + 1) * 5),
                visual_description=f"Segment {i}",
            )
            db_session.add(segment)

        await db_session.commit()

        with patch("app.services.user_content_analyzer.genai.Client"), patch(
            "app.services.user_content_analyzer.EmbeddingService"
        ), patch("app.services.user_content_analyzer.SupabaseStorage"):
            analyzer = UserContentAnalyzer()
            segments = await analyzer.get_project_segments(db_session, project.id)

            assert len(segments) == 3
            # Should be ordered by timestamp
            assert segments[0].timestamp_start == 0.0
            assert segments[1].timestamp_start == 5.0
            assert segments[2].timestamp_start == 10.0

    @pytest.mark.asyncio
    async def test_delete_file_segments(self, db_session):
        """Test deleting segments for a specific file."""
        # Create test project
        project = Project(
            id=uuid.uuid4(),
            name="Test Project",
        )
        db_session.add(project)

        # Create segments for two different files
        file_id_1 = uuid.uuid4()
        file_id_2 = uuid.uuid4()

        for i in range(2):
            segment = UserVideoSegment(
                project_id=project.id,
                source_file_id=file_id_1,
                source_file_name="file1.mp4",
                timestamp_start=float(i * 5),
                timestamp_end=float((i + 1) * 5),
                visual_description=f"File 1 Segment {i}",
            )
            db_session.add(segment)

        for i in range(3):
            segment = UserVideoSegment(
                project_id=project.id,
                source_file_id=file_id_2,
                source_file_name="file2.mp4",
                timestamp_start=float(i * 5),
                timestamp_end=float((i + 1) * 5),
                visual_description=f"File 2 Segment {i}",
            )
            db_session.add(segment)

        await db_session.commit()

        with patch("app.services.user_content_analyzer.genai.Client"), patch(
            "app.services.user_content_analyzer.EmbeddingService"
        ), patch("app.services.user_content_analyzer.SupabaseStorage"):
            analyzer = UserContentAnalyzer()

            # Delete segments for file 1
            deleted_count = await analyzer.delete_file_segments(db_session, file_id_1)

            assert deleted_count == 2

            # Verify only file 2 segments remain
            remaining = await analyzer.get_project_segments(db_session, project.id)
            assert len(remaining) == 3
            assert all(s.source_file_id == file_id_2 for s in remaining)


class TestUserContentAnalysisPrompt:
    """Tests for the analysis prompt."""

    def test_prompt_contains_key_instructions(self):
        """Verify prompt contains required instructions."""
        assert "ANALYSIS GOALS" in USER_CONTENT_ANALYSIS_PROMPT
        assert "timestamp_start" in USER_CONTENT_ANALYSIS_PROMPT
        assert "visual_description" in USER_CONTENT_ANALYSIS_PROMPT
        assert "action_tags" in USER_CONTENT_ANALYSIS_PROMPT
        assert "scene_type" in USER_CONTENT_ANALYSIS_PROMPT

    def test_prompt_includes_scene_types(self):
        """Verify prompt includes all scene type options."""
        scene_types = [
            "product_demo",
            "testimonial",
            "b_roll",
            "before_after",
            "lifestyle",
        ]
        for scene_type in scene_types:
            assert scene_type in USER_CONTENT_ANALYSIS_PROMPT

    def test_prompt_requests_json(self):
        """Verify prompt requests JSON output."""
        assert "JSON" in USER_CONTENT_ANALYSIS_PROMPT
        assert "EXACT JSON structure" in USER_CONTENT_ANALYSIS_PROMPT


class TestSegmentAnalysisSchema:
    """Tests for SegmentAnalysis schema."""

    def test_segment_analysis_validation(self):
        """Test valid SegmentAnalysis creation."""
        segment = SegmentAnalysis(
            timestamp_start=0.0,
            timestamp_end=5.0,
            visual_description="Test description",
            action_tags=["tag1", "tag2"],
        )

        assert segment.timestamp_start == 0.0
        assert segment.timestamp_end == 5.0
        assert len(segment.action_tags) == 2

    def test_segment_analysis_negative_timestamp_fails(self):
        """Test that negative timestamps are rejected."""
        with pytest.raises(ValueError):
            SegmentAnalysis(
                timestamp_start=-1.0,
                timestamp_end=5.0,
                visual_description="Test",
            )

    def test_segment_analysis_optional_fields(self):
        """Test optional fields default correctly."""
        segment = SegmentAnalysis(
            timestamp_start=0.0,
            timestamp_end=5.0,
            visual_description="Test",
        )

        assert segment.action_tags == []
        assert segment.scene_type is None
        assert segment.has_face is False
        assert segment.has_product is False


class TestVideoAnalysisResultSchema:
    """Tests for VideoAnalysisResult schema."""

    def test_video_analysis_result_creation(self):
        """Test creating VideoAnalysisResult."""
        result = VideoAnalysisResult(
            video_level_summary="Test summary",
            video_level_tags=["tag1"],
            total_duration_seconds=30.0,
            segments=[
                SegmentAnalysis(
                    timestamp_start=0.0,
                    timestamp_end=10.0,
                    visual_description="Test segment",
                )
            ],
        )

        assert result.video_level_summary == "Test summary"
        assert len(result.segments) == 1
        assert result.total_duration_seconds == 30.0

    def test_video_analysis_result_empty_segments(self):
        """Test VideoAnalysisResult with no segments."""
        result = VideoAnalysisResult(
            video_level_summary="Empty video",
            video_level_tags=[],
            total_duration_seconds=5.0,
        )

        assert len(result.segments) == 0
