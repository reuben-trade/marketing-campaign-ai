"""Tests for the Semantic Search Service, including project-scoped segment search."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.project import Project
from app.models.user_video_segment import UserVideoSegment
from app.services.semantic_search_service import SemanticSearchService


@pytest.fixture
def mock_embedding():
    """Generate a mock 1536-dimensional embedding vector."""
    return [0.1] * 1536


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return Project(
        id=uuid.uuid4(),
        name="Test Project",
        status="ready",
        user_prompt="Test prompt",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_segments(sample_project, mock_embedding):
    """Create sample video segments with embeddings for testing."""
    segments = []
    file_id = uuid.uuid4()

    segment_data = [
        {
            "visual_description": "Close-up of hands installing a faucet",
            "action_tags": ["hands", "installation", "faucet", "close-up"],
            "timestamp_start": 0.0,
            "timestamp_end": 5.0,
        },
        {
            "visual_description": "Person smiling and showing the finished result",
            "action_tags": ["testimonial", "happy", "result", "success"],
            "timestamp_start": 5.0,
            "timestamp_end": 12.0,
        },
        {
            "visual_description": "Water leaking from a broken faucet, frustrated homeowner",
            "action_tags": ["problem", "leak", "frustrated", "water"],
            "timestamp_start": 0.0,
            "timestamp_end": 4.0,
        },
        {
            "visual_description": "Energetic product reveal with surprise reaction",
            "action_tags": ["reveal", "energetic", "surprise", "product"],
            "timestamp_start": 0.0,
            "timestamp_end": 3.0,
        },
        {
            "visual_description": "Slow motion water drops",
            "action_tags": ["water", "slow-motion", "b-roll", "aesthetic"],
            "timestamp_start": 12.0,
            "timestamp_end": 16.0,
        },
    ]

    for i, data in enumerate(segment_data):
        segment = UserVideoSegment(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            source_file_id=file_id,
            source_file_name="test_video.mp4",
            source_file_url=f"https://example.com/videos/test_{i}.mp4",
            timestamp_start=data["timestamp_start"],
            timestamp_end=data["timestamp_end"],
            duration_seconds=data["timestamp_end"] - data["timestamp_start"],
            visual_description=data["visual_description"],
            action_tags=data["action_tags"],
            embedding=mock_embedding,
            thumbnail_url=f"https://example.com/thumbs/thumb_{i}.jpg",
            created_at=datetime.now(timezone.utc),
        )
        segments.append(segment)

    return segments


class TestSemanticSearchService:
    """Tests for SemanticSearchService class."""

    def test_init(self):
        """Test SemanticSearchService initialization."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()
            assert service.embedding_service is not None

    @pytest.mark.asyncio
    async def test_search_project_segments_basic(
        self, sample_project, sample_segments, mock_embedding
    ):
        """Test basic project segment search."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()

            # Mock embedding generation
            service.embedding_service.generate_embedding = AsyncMock(return_value=mock_embedding)

            # Mock database session
            mock_db = AsyncMock()

            # Mock the raw SQL query result (simplified: only id and similarity)
            mock_row = MagicMock()
            mock_row.id = sample_segments[0].id
            mock_row.similarity = 0.85

            # First execute returns the search query results
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [mock_row]

            # Second execute returns the batch-fetched segments
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = [sample_segments[0]]
            mock_batch_result = MagicMock()
            mock_batch_result.scalars.return_value = mock_scalars

            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_batch_result])

            results = await service.search_project_segments(
                db=mock_db,
                project_id=sample_project.id,
                query="hands installing faucet close-up",
                limit=10,
                min_similarity=0.5,
            )

            assert len(results) == 1
            segment, similarity = results[0]
            assert segment.id == sample_segments[0].id
            assert similarity == 0.85

            # Verify embedding was generated for the query
            service.embedding_service.generate_embedding.assert_called_once_with(
                "hands installing faucet close-up"
            )

    @pytest.mark.asyncio
    async def test_search_project_segments_filters_by_min_similarity(
        self, sample_project, sample_segments, mock_embedding
    ):
        """Test that results below min_similarity are filtered out."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()
            service.embedding_service.generate_embedding = AsyncMock(return_value=mock_embedding)

            mock_db = AsyncMock()

            # Create rows with varying similarities: 0.9, 0.6, 0.3
            # The third one (0.3) should be filtered out by min_similarity=0.5
            similarities = [0.9, 0.6, 0.3]
            mock_rows = []
            for i, seg in enumerate(sample_segments[:3]):
                mock_row = MagicMock()
                mock_row.id = seg.id
                mock_row.similarity = similarities[i]
                mock_rows.append(mock_row)

            mock_result = MagicMock()
            mock_result.fetchall.return_value = mock_rows

            # Batch fetch returns only segments that passed the filter (first 2)
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = [sample_segments[0], sample_segments[1]]
            mock_batch_result = MagicMock()
            mock_batch_result.scalars.return_value = mock_scalars

            mock_db.execute = AsyncMock(side_effect=[mock_result, mock_batch_result])

            results = await service.search_project_segments(
                db=mock_db,
                project_id=sample_project.id,
                query="test query",
                limit=10,
                min_similarity=0.5,  # Should filter out the 0.3 result
            )

            # Only 2 results should pass the min_similarity threshold
            assert len(results) == 2
            # Verify the similarities of returned results
            returned_similarities = [sim for _, sim in results]
            assert 0.9 in returned_similarities
            assert 0.6 in returned_similarities
            # The 0.3 result should NOT be in results
            assert 0.3 not in returned_similarities

    @pytest.mark.asyncio
    async def test_search_project_segments_empty_results(self, sample_project, mock_embedding):
        """Test search with no matching segments."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()
            service.embedding_service.generate_embedding = AsyncMock(return_value=mock_embedding)

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            mock_db.execute = AsyncMock(return_value=mock_result)

            results = await service.search_project_segments(
                db=mock_db,
                project_id=sample_project.id,
                query="nonexistent content",
                limit=10,
            )

            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_project_segments_batch(
        self, sample_project, sample_segments, mock_embedding
    ):
        """Test batch search for multiple queries."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()

            # Mock the single search method
            service.search_project_segments = AsyncMock(
                side_effect=[
                    [(sample_segments[0], 0.85)],
                    [(sample_segments[1], 0.78)],
                    [(sample_segments[2], 0.72)],
                ]
            )

            mock_db = AsyncMock()
            queries = [
                "hands installation close-up",
                "happy testimonial success",
                "water leak problem",
            ]

            results = await service.search_project_segments_batch(
                db=mock_db,
                project_id=sample_project.id,
                queries=queries,
                limit_per_query=5,
            )

            assert len(results) == 3
            assert queries[0] in results
            assert queries[1] in results
            assert queries[2] in results

            # Verify each query was searched
            assert service.search_project_segments.call_count == 3

    @pytest.mark.asyncio
    async def test_search_slots_in_project(self, sample_project, sample_segments, mock_embedding):
        """Test searching for clips matching visual script slots."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()

            # Mock the single search method
            service.search_project_segments = AsyncMock(
                side_effect=[
                    [(sample_segments[3], 0.89), (sample_segments[0], 0.76)],
                    [(sample_segments[2], 0.82)],
                    [(sample_segments[1], 0.85)],
                ]
            )

            mock_db = AsyncMock()
            slots = [
                {
                    "id": "slot_01_hook",
                    "beat_type": "Hook",
                    "search_query": "energetic action, product reveal, surprised reaction",
                },
                {
                    "id": "slot_02_problem",
                    "beat_type": "Problem",
                    "search_query": "frustrated expression, leak, water problem",
                },
                {
                    "id": "slot_03_cta",
                    "beat_type": "CTA",
                    "search_query": "happy result, satisfied customer, success",
                },
            ]

            results = await service.search_slots_in_project(
                db=mock_db,
                project_id=sample_project.id,
                slots=slots,
                limit_per_slot=5,
            )

            assert len(results) == 3
            assert "slot_01_hook" in results
            assert "slot_02_problem" in results
            assert "slot_03_cta" in results

            # Hook slot should have 2 results
            assert len(results["slot_01_hook"]) == 2
            assert results["slot_01_hook"][0][1] == 0.89  # Higher similarity first

    @pytest.mark.asyncio
    async def test_search_slots_in_project_skips_invalid_slots(
        self, sample_project, mock_embedding
    ):
        """Test that slots without id or search_query are skipped."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()
            service.search_project_segments = AsyncMock(return_value=[])

            mock_db = AsyncMock()
            slots = [
                {"id": "valid_slot", "search_query": "valid query"},
                {"id": "missing_query"},  # Missing search_query
                {"search_query": "missing id"},  # Missing id
                {},  # Empty slot
            ]

            results = await service.search_slots_in_project(
                db=mock_db,
                project_id=sample_project.id,
                slots=slots,
            )

            # Only the valid slot should be searched
            assert len(results) == 1
            assert "valid_slot" in results
            service.search_project_segments.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_similar_segments_in_project(
        self, sample_project, sample_segments, mock_embedding
    ):
        """Test finding segments similar to a specific segment."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()

            mock_db = AsyncMock()

            # First call returns the source segment
            source_segment = sample_segments[0]
            mock_source_result = MagicMock()
            mock_source_result.scalar_one_or_none.return_value = source_segment

            # Second call returns similar segment rows (simplified: only id and similarity)
            mock_row = MagicMock()
            mock_row.id = sample_segments[1].id
            mock_row.similarity = 0.75
            mock_search_result = MagicMock()
            mock_search_result.fetchall.return_value = [mock_row]

            # Third call batch fetches the full similar segments
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = [sample_segments[1]]
            mock_batch_result = MagicMock()
            mock_batch_result.scalars.return_value = mock_scalars

            mock_db.execute = AsyncMock(
                side_effect=[mock_source_result, mock_search_result, mock_batch_result]
            )

            results = await service.find_similar_segments_in_project(
                db=mock_db,
                segment_id=source_segment.id,
                project_id=sample_project.id,
                limit=5,
                min_similarity=0.6,
            )

            assert len(results) == 1
            similar_segment, similarity = results[0]
            assert similar_segment.id == sample_segments[1].id
            assert similarity == 0.75

    @pytest.mark.asyncio
    async def test_find_similar_segments_segment_not_found(self, sample_project):
        """Test handling when source segment doesn't exist."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_result)

            results = await service.find_similar_segments_in_project(
                db=mock_db,
                segment_id=uuid.uuid4(),  # Non-existent segment
                project_id=sample_project.id,
            )

            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_find_similar_segments_no_embedding(self, sample_project):
        """Test handling when source segment has no embedding."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()

            # Create segment without embedding
            segment_no_embedding = UserVideoSegment(
                id=uuid.uuid4(),
                project_id=sample_project.id,
                source_file_id=uuid.uuid4(),
                source_file_name="test.mp4",
                timestamp_start=0.0,
                timestamp_end=5.0,
                visual_description="Test segment",
                embedding=None,  # No embedding
                created_at=datetime.now(timezone.utc),
            )

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = segment_no_embedding
            mock_db.execute = AsyncMock(return_value=mock_result)

            results = await service.find_similar_segments_in_project(
                db=mock_db,
                segment_id=segment_no_embedding.id,
                project_id=sample_project.id,
            )

            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_find_similar_segments_wrong_project(self, sample_project, mock_embedding):
        """Test handling when segment belongs to different project."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()

            # Create segment belonging to different project
            different_project_id = uuid.uuid4()
            segment = UserVideoSegment(
                id=uuid.uuid4(),
                project_id=different_project_id,  # Different project
                source_file_id=uuid.uuid4(),
                source_file_name="test.mp4",
                timestamp_start=0.0,
                timestamp_end=5.0,
                visual_description="Test segment",
                embedding=mock_embedding,
                created_at=datetime.now(timezone.utc),
            )

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = segment
            mock_db.execute = AsyncMock(return_value=mock_result)

            results = await service.find_similar_segments_in_project(
                db=mock_db,
                segment_id=segment.id,
                project_id=sample_project.id,  # Different from segment's project
            )

            assert len(results) == 0


class TestSearchIntegrationWithVisualScript:
    """Test semantic search integration with visual script slots from ContentPlanningAgent."""

    @pytest.mark.asyncio
    async def test_full_slot_search_workflow(self, sample_project, sample_segments, mock_embedding):
        """Test the full workflow of searching for clips matching a visual script."""
        with patch("app.services.embedding_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            service = SemanticSearchService()

            # Simulate visual script output from ContentPlanningAgent
            visual_script_slots = [
                {
                    "id": "slot_01_hook",
                    "beat_type": "Hook",
                    "target_duration": 3.0,
                    "search_query": "energetic action, product reveal, surprised reaction",
                    "overlay_text": "Stop Wasting Money!",
                    "text_position": "center",
                },
                {
                    "id": "slot_02_problem",
                    "beat_type": "Problem",
                    "target_duration": 5.0,
                    "search_query": "frustrated expression, leak, water problem",
                    "overlay_text": "Tired of leaky faucets?",
                    "text_position": "bottom",
                },
                {
                    "id": "slot_03_solution",
                    "beat_type": "Solution",
                    "target_duration": 8.0,
                    "search_query": "hands installing, product demo, close-up work",
                    "overlay_text": "Easy Fix in Minutes",
                    "text_position": "bottom",
                },
                {
                    "id": "slot_04_cta",
                    "beat_type": "CTA",
                    "target_duration": 4.0,
                    "search_query": "happy result, satisfied customer, success",
                    "overlay_text": "Shop Now!",
                    "text_position": "center",
                },
            ]

            # Mock search to return different segments for each slot
            search_results = [
                [(sample_segments[3], 0.89)],  # Hook -> energetic reveal
                [(sample_segments[2], 0.82)],  # Problem -> leak/frustrated
                [(sample_segments[0], 0.91)],  # Solution -> hands installing
                [(sample_segments[1], 0.85)],  # CTA -> happy result
            ]
            service.search_project_segments = AsyncMock(side_effect=search_results)

            mock_db = AsyncMock()

            results = await service.search_slots_in_project(
                db=mock_db,
                project_id=sample_project.id,
                slots=visual_script_slots,
                limit_per_slot=3,
                min_similarity=0.5,
            )

            # Verify we got results for all 4 slots
            assert len(results) == 4

            # Verify slot IDs match
            assert "slot_01_hook" in results
            assert "slot_02_problem" in results
            assert "slot_03_solution" in results
            assert "slot_04_cta" in results

            # Verify best match for each slot
            assert results["slot_01_hook"][0][0].id == sample_segments[3].id  # Energetic
            assert results["slot_02_problem"][0][0].id == sample_segments[2].id  # Frustrated
            assert results["slot_03_solution"][0][0].id == sample_segments[0].id  # Hands
            assert results["slot_04_cta"][0][0].id == sample_segments[1].id  # Happy

            # Verify search was called 4 times (once per slot)
            assert service.search_project_segments.call_count == 4
