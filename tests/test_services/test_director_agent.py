"""Tests for the Director Agent service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user_video_segment import UserVideoSegment
from app.models.visual_script import VisualScript
from app.schemas.remotion_payload import (
    GeneratedBRollSource,
    CompositionType,
    DirectorAgentInput,
    RemotionPayload,
    SegmentType,
    TextPosition,
    TimelineSegment,
    TransitionType,
)
from app.schemas.visual_script import VisualScriptSlot
from app.services.director_agent import DirectorAgent, DirectorAgentError


@pytest.fixture
def director_agent():
    """Create a Director Agent instance."""
    return DirectorAgent()


@pytest.fixture
def sample_project():
    """Create a sample project."""
    return Project(
        id=uuid.uuid4(),
        name="Test Project",
        status="ready",
        max_videos=10,
        max_total_size_mb=500,
    )


@pytest.fixture
def sample_visual_script(sample_project):
    """Create a sample visual script."""
    return VisualScript(
        id=uuid.uuid4(),
        project_id=sample_project.id,
        recipe_id=uuid.uuid4(),
        total_duration_seconds=30,
        slots=[
            {
                "id": "slot_01_hook",
                "beat_type": "hook",
                "target_duration": 3.0,
                "search_query": "energetic action, product reveal",
                "overlay_text": "Stop Wasting Money!",
                "text_position": "center",
                "transition_out": "wipe_right",
                "notes": "Need high-energy opening",
                "characteristics": ["fast_cuts", "bold_text"],
            },
            {
                "id": "slot_02_problem",
                "beat_type": "problem",
                "target_duration": 5.0,
                "search_query": "frustrated expression, broken item",
                "overlay_text": "Tired of leaky faucets?",
                "text_position": "bottom",
                "transition_out": "cut",
            },
            {
                "id": "slot_03_solution",
                "beat_type": "solution",
                "target_duration": 8.0,
                "search_query": "product demo, installation, success",
                "overlay_text": None,
                "text_position": None,
                "transition_out": "dissolve",
            },
        ],
        audio_suggestion="upbeat_trending",
        pacing_notes="Fast cuts in hook, slower in demo",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_segments(sample_project):
    """Create sample user video segments."""
    file_id = uuid.uuid4()
    return [
        UserVideoSegment(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            source_file_id=file_id,
            source_file_name="demo_video.mp4",
            source_file_url="https://storage.example.com/demo_video.mp4",
            timestamp_start=0.0,
            timestamp_end=3.5,
            duration_seconds=3.5,
            visual_description="Person excitedly holding product",
            action_tags=["excited", "product", "reveal"],
            embedding=[0.1] * 1536,
        ),
        UserVideoSegment(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            source_file_id=file_id,
            source_file_name="demo_video.mp4",
            source_file_url="https://storage.example.com/demo_video.mp4",
            timestamp_start=10.0,
            timestamp_end=15.5,
            duration_seconds=5.5,
            visual_description="Person looking frustrated at broken faucet",
            action_tags=["frustrated", "problem", "faucet"],
            embedding=[0.2] * 1536,
        ),
        UserVideoSegment(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            source_file_id=file_id,
            source_file_name="demo_video.mp4",
            source_file_url="https://storage.example.com/demo_video.mp4",
            timestamp_start=20.0,
            timestamp_end=28.0,
            duration_seconds=8.0,
            visual_description="Hands installing new faucet, success",
            action_tags=["installation", "demo", "success"],
            embedding=[0.3] * 1536,
        ),
    ]


@pytest.fixture
def sample_project_files(sample_project, sample_segments):
    """Create sample project files."""
    file_id = sample_segments[0].source_file_id
    return [
        ProjectFile(
            id=file_id,
            project_id=sample_project.id,
            filename="demo_video.mp4",
            original_filename="demo_video.mp4",
            storage_path="projects/test/demo_video.mp4",
            file_url="https://storage.example.com/demo_video.mp4",
            file_size_bytes=10000000,
            content_type="video/mp4",
            status="completed",
        )
    ]


class TestDirectorAgent:
    """Tests for DirectorAgent class."""

    @pytest.mark.asyncio
    async def test_assemble_success(
        self,
        director_agent,
        sample_project,
        sample_visual_script,
        sample_segments,
        sample_project_files,
    ):
        """Test successful assembly of Remotion payload."""
        mock_db = AsyncMock()

        # Mock database queries
        with patch.object(
            director_agent, "_get_visual_script", return_value=sample_visual_script
        ), patch.object(director_agent, "_get_project", return_value=sample_project), patch.object(
            director_agent,
            "_build_file_url_map",
            return_value={sample_project_files[0].id: sample_project_files[0].file_url},
        ), patch.object(
            director_agent.semantic_search,
            "search_slots_in_project",
            return_value={
                "slot_01_hook": [(sample_segments[0], 0.89)],
                "slot_02_problem": [(sample_segments[1], 0.85)],
                "slot_03_solution": [(sample_segments[2], 0.92)],
            },
        ):
            input_data = DirectorAgentInput(
                project_id=sample_project.id,
                visual_script_id=sample_visual_script.id,
                composition_type=CompositionType.VERTICAL,
                min_similarity_threshold=0.5,
                gap_handling="broll",
            )

            result = await director_agent.assemble(mock_db, input_data)

            assert result.success is True
            assert result.error_message is None
            assert result.payload is not None
            assert len(result.payload.timeline) == 3
            assert result.stats["clips_selected"] == 3
            assert result.stats["gaps_detected"] == 0

    @pytest.mark.asyncio
    async def test_assemble_with_gaps(
        self,
        director_agent,
        sample_project,
        sample_visual_script,
        sample_segments,
        sample_project_files,
    ):
        """Test assembly with gaps (no matching clips for some slots)."""
        mock_db = AsyncMock()

        with patch.object(
            director_agent, "_get_visual_script", return_value=sample_visual_script
        ), patch.object(director_agent, "_get_project", return_value=sample_project), patch.object(
            director_agent,
            "_build_file_url_map",
            return_value={sample_project_files[0].id: sample_project_files[0].file_url},
        ), patch.object(
            director_agent.semantic_search,
            "search_slots_in_project",
            return_value={
                "slot_01_hook": [(sample_segments[0], 0.89)],
                "slot_02_problem": [],  # No results - gap
                "slot_03_solution": [(sample_segments[2], 0.92)],
            },
        ):
            input_data = DirectorAgentInput(
                project_id=sample_project.id,
                visual_script_id=sample_visual_script.id,
                composition_type=CompositionType.VERTICAL,
                min_similarity_threshold=0.5,
                gap_handling="broll",
            )

            result = await director_agent.assemble(mock_db, input_data)

            assert result.success is True
            assert result.stats["clips_selected"] == 2
            assert result.stats["gaps_detected"] == 1
            assert result.payload.gaps is not None
            assert len(result.payload.gaps) == 1
            assert result.payload.gaps[0]["slot_id"] == "slot_02_problem"

    @pytest.mark.asyncio
    async def test_assemble_gap_handling_text_slide(
        self,
        director_agent,
        sample_project,
        sample_visual_script,
        sample_segments,
        sample_project_files,
    ):
        """Test gap handling with text slides."""
        mock_db = AsyncMock()

        with patch.object(
            director_agent, "_get_visual_script", return_value=sample_visual_script
        ), patch.object(director_agent, "_get_project", return_value=sample_project), patch.object(
            director_agent,
            "_build_file_url_map",
            return_value={sample_project_files[0].id: sample_project_files[0].file_url},
        ), patch.object(
            director_agent.semantic_search,
            "search_slots_in_project",
            return_value={
                "slot_01_hook": [],  # Gap
                "slot_02_problem": [],  # Gap
                "slot_03_solution": [(sample_segments[2], 0.92)],
            },
        ):
            input_data = DirectorAgentInput(
                project_id=sample_project.id,
                visual_script_id=sample_visual_script.id,
                gap_handling="text_slide",
            )

            result = await director_agent.assemble(mock_db, input_data)

            assert result.success is True
            # Check that gaps became text slides
            gap_segments = [s for s in result.payload.timeline if s.type == SegmentType.TEXT_SLIDE]
            assert len(gap_segments) == 2

    @pytest.mark.asyncio
    async def test_assemble_gap_handling_skip(
        self,
        director_agent,
        sample_project,
        sample_visual_script,
        sample_segments,
        sample_project_files,
    ):
        """Test gap handling with skip option."""
        mock_db = AsyncMock()

        with patch.object(
            director_agent, "_get_visual_script", return_value=sample_visual_script
        ), patch.object(director_agent, "_get_project", return_value=sample_project), patch.object(
            director_agent,
            "_build_file_url_map",
            return_value={sample_project_files[0].id: sample_project_files[0].file_url},
        ), patch.object(
            director_agent.semantic_search,
            "search_slots_in_project",
            return_value={
                "slot_01_hook": [],  # Gap - will be skipped
                "slot_02_problem": [(sample_segments[1], 0.85)],
                "slot_03_solution": [(sample_segments[2], 0.92)],
            },
        ):
            input_data = DirectorAgentInput(
                project_id=sample_project.id,
                visual_script_id=sample_visual_script.id,
                gap_handling="skip",
            )

            result = await director_agent.assemble(mock_db, input_data)

            assert result.success is True
            # Only 2 segments (gap was skipped)
            assert len(result.payload.timeline) == 2
            assert result.stats["gaps_detected"] == 1

    @pytest.mark.asyncio
    async def test_assemble_composition_types(
        self,
        director_agent,
        sample_project,
        sample_visual_script,
        sample_segments,
        sample_project_files,
    ):
        """Test different composition types set correct dimensions."""
        mock_db = AsyncMock()

        with patch.object(
            director_agent, "_get_visual_script", return_value=sample_visual_script
        ), patch.object(director_agent, "_get_project", return_value=sample_project), patch.object(
            director_agent,
            "_build_file_url_map",
            return_value={sample_project_files[0].id: sample_project_files[0].file_url},
        ), patch.object(
            director_agent.semantic_search,
            "search_slots_in_project",
            return_value={
                "slot_01_hook": [(sample_segments[0], 0.89)],
                "slot_02_problem": [(sample_segments[1], 0.85)],
                "slot_03_solution": [(sample_segments[2], 0.92)],
            },
        ):
            # Test vertical (9:16)
            input_data = DirectorAgentInput(
                project_id=sample_project.id,
                visual_script_id=sample_visual_script.id,
                composition_type=CompositionType.VERTICAL,
            )
            result = await director_agent.assemble(mock_db, input_data)
            assert result.payload.width == 1080
            assert result.payload.height == 1920

            # Test horizontal (16:9)
            input_data.composition_type = CompositionType.HORIZONTAL
            result = await director_agent.assemble(mock_db, input_data)
            assert result.payload.width == 1920
            assert result.payload.height == 1080

            # Test square (1:1)
            input_data.composition_type = CompositionType.SQUARE
            result = await director_agent.assemble(mock_db, input_data)
            assert result.payload.width == 1080
            assert result.payload.height == 1080

    @pytest.mark.asyncio
    async def test_assemble_with_audio(
        self,
        director_agent,
        sample_project,
        sample_visual_script,
        sample_segments,
        sample_project_files,
    ):
        """Test assembly with audio track."""
        mock_db = AsyncMock()

        with patch.object(
            director_agent, "_get_visual_script", return_value=sample_visual_script
        ), patch.object(director_agent, "_get_project", return_value=sample_project), patch.object(
            director_agent,
            "_build_file_url_map",
            return_value={sample_project_files[0].id: sample_project_files[0].file_url},
        ), patch.object(
            director_agent.semantic_search,
            "search_slots_in_project",
            return_value={
                "slot_01_hook": [(sample_segments[0], 0.89)],
                "slot_02_problem": [(sample_segments[1], 0.85)],
                "slot_03_solution": [(sample_segments[2], 0.92)],
            },
        ):
            input_data = DirectorAgentInput(
                project_id=sample_project.id,
                visual_script_id=sample_visual_script.id,
                audio_url="https://storage.example.com/audio/upbeat.mp3",
            )

            result = await director_agent.assemble(mock_db, input_data)

            assert result.payload.audio_track is not None
            assert result.payload.audio_track.url == "https://storage.example.com/audio/upbeat.mp3"
            assert result.payload.audio_track.volume == 0.8

    @pytest.mark.asyncio
    async def test_assemble_visual_script_not_found(self, director_agent, sample_project):
        """Test error when visual script not found."""
        mock_db = AsyncMock()

        with patch.object(
            director_agent, "_get_visual_script", side_effect=DirectorAgentError("not found")
        ):
            input_data = DirectorAgentInput(
                project_id=sample_project.id,
                visual_script_id=uuid.uuid4(),
            )

            with pytest.raises(DirectorAgentError):
                await director_agent.assemble(mock_db, input_data)

    @pytest.mark.asyncio
    async def test_assemble_project_not_found(
        self, director_agent, sample_project, sample_visual_script
    ):
        """Test error when project not found."""
        mock_db = AsyncMock()

        with patch.object(
            director_agent, "_get_visual_script", return_value=sample_visual_script
        ), patch.object(
            director_agent, "_get_project", side_effect=DirectorAgentError("not found")
        ):
            input_data = DirectorAgentInput(
                project_id=uuid.uuid4(),
                visual_script_id=sample_visual_script.id,
            )

            with pytest.raises(DirectorAgentError):
                await director_agent.assemble(mock_db, input_data)


class TestClipSelection:
    """Tests for clip selection logic."""

    def test_select_clip_no_results(self, director_agent):
        """Test clip selection with no search results."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="hook",
            target_duration=3.0,
            search_query="test query",
        )

        result = director_agent._select_clip_for_slot(
            slot=slot,
            search_results=[],
            file_url_map={},
            min_similarity=0.5,
        )

        assert result.selected is False
        assert result.gap_reason == "No search results returned"

    def test_select_clip_below_threshold(self, director_agent, sample_segments):
        """Test clip selection when similarity is below threshold."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="hook",
            target_duration=3.0,
            search_query="test query",
        )

        result = director_agent._select_clip_for_slot(
            slot=slot,
            search_results=[(sample_segments[0], 0.3)],  # Below 0.5 threshold
            file_url_map={sample_segments[0].source_file_id: "https://example.com/video.mp4"},
            min_similarity=0.5,
        )

        assert result.selected is False
        assert "threshold" in result.gap_reason.lower()

    def test_select_clip_success(self, director_agent, sample_segments):
        """Test successful clip selection."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="hook",
            target_duration=3.0,
            search_query="test query",
        )

        result = director_agent._select_clip_for_slot(
            slot=slot,
            search_results=[(sample_segments[0], 0.89)],
            file_url_map={sample_segments[0].source_file_id: "https://example.com/video.mp4"},
            min_similarity=0.5,
        )

        assert result.selected is True
        assert result.segment_id == sample_segments[0].id
        assert result.similarity_score == 0.89

    def test_select_best_clip_from_multiple(self, director_agent, sample_segments):
        """Test selection of best clip from multiple candidates."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="hook",
            target_duration=3.0,
            search_query="test query",
        )

        # First segment has lower similarity but better duration match
        # Second segment has higher similarity
        file_url = "https://example.com/video.mp4"
        file_url_map = {
            sample_segments[0].source_file_id: file_url,
            sample_segments[1].source_file_id: file_url,
        }

        result = director_agent._select_clip_for_slot(
            slot=slot,
            search_results=[
                (sample_segments[0], 0.75),  # 3.5s duration, close to 3s target
                (sample_segments[1], 0.85),  # 5.5s duration, further from target
            ],
            file_url_map=file_url_map,
            min_similarity=0.5,
        )

        assert result.selected is True
        # With 70/30 weighting, first segment wins due to better duration match
        assert result.segment_id == sample_segments[0].id


class TestSegmentCreation:
    """Tests for timeline segment creation."""

    def test_create_video_segment_with_overlay(self, director_agent, sample_segments):
        """Test creating video segment with text overlay."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="hook",
            target_duration=3.0,
            search_query="test query",
            overlay_text="Test Overlay",
            text_position="center",
            transition_out="wipe_right",
        )

        from app.schemas.remotion_payload import ClipSelectionResult

        selection = ClipSelectionResult(
            slot_id="test_slot",
            selected=True,
            segment_id=sample_segments[0].id,
            source_file_url="https://example.com/video.mp4",
            timestamp_start=0.0,
            timestamp_end=3.5,
            similarity_score=0.89,
            alternatives=[],
        )

        segment = director_agent._create_video_segment(
            slot=slot,
            selection=selection,
            start_frame=0,
            target_frames=90,
        )

        assert segment.type == SegmentType.VIDEO_CLIP
        assert segment.overlay is not None
        assert segment.overlay.text == "Test Overlay"
        assert segment.overlay.position == TextPosition.CENTER
        assert segment.transition_out is not None
        assert segment.transition_out.type == TransitionType.WIPE_RIGHT

    def test_create_video_segment_without_overlay(self, director_agent, sample_segments):
        """Test creating video segment without text overlay."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="solution",
            target_duration=8.0,
            search_query="test query",
        )

        from app.schemas.remotion_payload import ClipSelectionResult

        selection = ClipSelectionResult(
            slot_id="test_slot",
            selected=True,
            segment_id=sample_segments[2].id,
            source_file_url="https://example.com/video.mp4",
            timestamp_start=20.0,
            timestamp_end=28.0,
            similarity_score=0.92,
            alternatives=[],
        )

        segment = director_agent._create_video_segment(
            slot=slot,
            selection=selection,
            start_frame=180,
            target_frames=240,
        )

        assert segment.type == SegmentType.VIDEO_CLIP
        assert segment.overlay is None
        assert segment.source.start_time == 20.0
        assert segment.source.end_time == 28.0


class TestGapHandling:
    """Tests for gap handling logic."""

    def test_handle_gap_broll(self, director_agent):
        """Test gap handling with B-Roll generation."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="problem",
            target_duration=5.0,
            search_query="frustrated person, broken item",
            overlay_text="Having issues?",
            characteristics=["emotional", "relatable"],
        )

        from app.schemas.remotion_payload import ClipSelectionResult

        selection = ClipSelectionResult(
            slot_id="test_slot",
            selected=False,
            gap_reason="No matching clips",
            alternatives=[],
        )

        segment = director_agent._handle_gap(
            slot=slot,
            selection=selection,
            start_frame=90,
            target_frames=150,
            gap_handling="broll",
        )

        assert segment is not None
        assert segment.type == SegmentType.GENERATED_BROLL
        assert segment.generated_source is not None
        assert "frustrated person" in segment.generated_source.generation_prompt

    def test_handle_gap_text_slide(self, director_agent):
        """Test gap handling with text slide."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="cta",
            target_duration=3.0,
            search_query="call to action",
            overlay_text="Shop Now!",
        )

        from app.schemas.remotion_payload import ClipSelectionResult

        selection = ClipSelectionResult(
            slot_id="test_slot",
            selected=False,
            gap_reason="No matching clips",
            alternatives=[],
        )

        segment = director_agent._handle_gap(
            slot=slot,
            selection=selection,
            start_frame=270,
            target_frames=90,
            gap_handling="text_slide",
        )

        assert segment is not None
        assert segment.type == SegmentType.TEXT_SLIDE
        assert segment.text_content is not None
        assert segment.text_content.headline == "Shop Now!"

    def test_handle_gap_skip(self, director_agent):
        """Test gap handling with skip option."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="transition",
            target_duration=2.0,
            search_query="transition shot",
        )

        from app.schemas.remotion_payload import ClipSelectionResult

        selection = ClipSelectionResult(
            slot_id="test_slot",
            selected=False,
            gap_reason="No matching clips",
            alternatives=[],
        )

        segment = director_agent._handle_gap(
            slot=slot,
            selection=selection,
            start_frame=0,
            target_frames=60,
            gap_handling="skip",
        )

        assert segment is None


class TestBRollPromptGeneration:
    """Tests for B-Roll prompt generation."""

    def test_generate_broll_prompt_basic(self, director_agent):
        """Test basic B-Roll prompt generation."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="problem",
            target_duration=5.0,
            search_query="water dripping from faucet",
        )

        prompt = director_agent._generate_broll_prompt(slot)

        assert "water dripping from faucet" in prompt
        assert "problem" in prompt.lower()
        assert "5.0 seconds" in prompt

    def test_generate_broll_prompt_with_cinematics(self, director_agent):
        """Test B-Roll prompt with cinematic requirements."""
        slot = VisualScriptSlot(
            id="test_slot",
            beat_type="hook",
            target_duration=3.0,
            search_query="product reveal",
            characteristics=["dramatic", "slow_motion"],
            cinematics={
                "camera_angle": "low_angle",
                "lighting": "dramatic",
                "motion_type": "slow_motion",
            },
        )

        prompt = director_agent._generate_broll_prompt(slot)

        assert "product reveal" in prompt
        assert "dramatic" in prompt.lower()
        assert "slow_motion" in prompt.lower() or "slow motion" in prompt.lower()
        assert "low_angle" in prompt


class TestStatisticsCalculation:
    """Tests for assembly statistics calculation."""

    def test_calculate_stats(self, director_agent):
        """Test statistics calculation."""
        from app.schemas.remotion_payload import ClipSelectionResult

        clip_selections = [
            ClipSelectionResult(
                slot_id="slot_1", selected=True, similarity_score=0.89, alternatives=[]
            ),
            ClipSelectionResult(
                slot_id="slot_2", selected=True, similarity_score=0.75, alternatives=[]
            ),
            ClipSelectionResult(
                slot_id="slot_3", selected=False, gap_reason="No clips", alternatives=[]
            ),
        ]
        gaps = [{"slot_id": "slot_3", "reason": "No clips"}]

        stats = director_agent._calculate_stats(
            clip_selections=clip_selections,
            gaps=gaps,
            total_frames=480,
        )

        assert stats["total_slots"] == 3
        assert stats["clips_selected"] == 2
        assert stats["gaps_detected"] == 1
        assert stats["coverage_percentage"] == pytest.approx(66.67, rel=0.1)
        assert stats["average_similarity"] == pytest.approx(0.82, rel=0.01)
        assert stats["total_duration_seconds"] == 16.0  # 480 / 30 fps


class TestPayloadUpdate:
    """Tests for payload update functionality."""

    @pytest.mark.asyncio
    async def test_update_segment_clip(self, director_agent, sample_segments):
        """Test updating a segment with a new clip."""

        # Create initial payload with a gap segment
        payload = RemotionPayload(
            composition_id=CompositionType.VERTICAL,
            width=1080,
            height=1920,
            fps=30,
            duration_in_frames=300,
            project_id=uuid.uuid4(),
            timeline=[
                TimelineSegment(
                    id="segment_gap",
                    type=SegmentType.GENERATED_BROLL,
                    start_frame=0,
                    duration_frames=90,
                    generated_source=GeneratedBRollSource(
                        generation_prompt="test prompt",
                        regenerate_available=True,
                    ),
                    slot_id="slot_01",
                    search_query="test query",
                )
            ],
            version=1,
        )

        # Update with a video clip
        updated_payload = await director_agent.update_segment_clip(
            payload=payload,
            segment_id="segment_gap",
            new_segment=sample_segments[0],
            source_url="https://example.com/video.mp4",
        )

        assert updated_payload.version == 2
        assert updated_payload.timeline[0].type == SegmentType.VIDEO_CLIP
        assert updated_payload.timeline[0].source is not None
        assert updated_payload.timeline[0].source.url == "https://example.com/video.mp4"

    @pytest.mark.asyncio
    async def test_get_clip_alternatives(self, director_agent, sample_segments):
        """Test getting alternative clips for a slot."""
        mock_db = AsyncMock()
        project_id = uuid.uuid4()

        with patch.object(
            director_agent.semantic_search,
            "search_project_segments",
            return_value=[
                (sample_segments[0], 0.89),
                (sample_segments[1], 0.75),
            ],
        ), patch.object(
            director_agent,
            "_build_file_url_map",
            return_value={
                sample_segments[0].source_file_id: "https://example.com/video.mp4",
            },
        ):
            alternatives = await director_agent.get_clip_alternatives(
                db=mock_db,
                project_id=project_id,
                slot_id="test_slot",
                search_query="test query",
                limit=10,
            )

            assert len(alternatives) == 2
            assert alternatives[0]["similarity_score"] == 0.89
            assert "visual_description" in alternatives[0]


