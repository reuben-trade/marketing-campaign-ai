"""Tests for the Content Planning Agent service."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.brand_profile import BrandProfile
from app.models.project import Project
from app.models.recipe import Recipe
from app.models.user_video_segment import UserVideoSegment
from app.schemas.visual_script import (
    ContentPlanningInput,
    ContentPlanningOutput,
    VisualScriptSlot,
)
from app.services.content_planner import ContentPlanningAgent, ContentPlanningError


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI response with valid visual script JSON."""
    return {
        "slots": [
            {
                "id": "slot_01_hook",
                "beat_type": "Hook",
                "target_duration": 3.0,
                "search_query": "energetic action, product reveal, surprised reaction",
                "overlay_text": "Stop Wasting Money!",
                "text_position": "center",
                "transition_in": None,
                "transition_out": "cut",
                "notes": "Need high-energy opening",
                "characteristics": ["fast_cuts", "bold_text"],
                "cinematics": {"camera_angle": "close-up", "motion_type": "handheld"},
            },
            {
                "id": "slot_02_problem",
                "beat_type": "Problem",
                "target_duration": 5.0,
                "search_query": "frustrated expression, difficulty, problem",
                "overlay_text": "Tired of leaky faucets?",
                "text_position": "bottom",
                "transition_in": "cut",
                "transition_out": "dissolve",
                "notes": "Show the pain point",
                "characteristics": ["relatable_scenario"],
                "cinematics": {"camera_angle": "medium"},
            },
            {
                "id": "slot_03_solution",
                "beat_type": "Solution",
                "target_duration": 8.0,
                "search_query": "product demo, fixing, installation, hands working",
                "overlay_text": "Easy Fix in Minutes",
                "text_position": "bottom",
                "transition_in": "dissolve",
                "transition_out": "cut",
                "notes": "Show product in action",
                "characteristics": ["product_demo", "hands"],
                "cinematics": {"camera_angle": "close-up"},
            },
            {
                "id": "slot_04_cta",
                "beat_type": "CTA",
                "target_duration": 4.0,
                "search_query": "happy result, satisfied customer, success",
                "overlay_text": "Shop Now - 50% Off!",
                "text_position": "center",
                "transition_in": "cut",
                "transition_out": None,
                "notes": "Strong call to action",
                "characteristics": ["urgency", "clear_action"],
                "cinematics": None,
            },
        ],
        "total_duration_seconds": 20,
        "audio_suggestion": "upbeat_trending",
        "pacing_notes": "Fast cuts in hook, slower in demo, build urgency for CTA",
        "planning_notes": ["User has good demo content", "Consider testimonial for social proof"],
    }


@pytest.fixture
def sample_recipe():
    """Create a sample recipe for testing."""
    return Recipe(
        id=uuid.uuid4(),
        name="Hook + PAS + CTA",
        source_ad_id=None,
        total_duration_seconds=20,
        structure=[
            {
                "beat_type": "Hook",
                "target_duration": 3.0,
                "characteristics": ["fast_cuts", "bold_text"],
                "purpose": "Stop the scroll",
            },
            {
                "beat_type": "Problem",
                "target_duration": 5.0,
                "characteristics": ["relatable_scenario"],
                "purpose": "Identify with viewer",
            },
            {
                "beat_type": "Solution",
                "target_duration": 8.0,
                "characteristics": ["product_demo"],
                "purpose": "Show the fix",
            },
            {
                "beat_type": "CTA",
                "target_duration": 4.0,
                "characteristics": ["urgency"],
                "purpose": "Drive conversion",
            },
        ],
        pacing="fast",
        style="ugc",
        composite_score=0.85,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return Project(
        id=uuid.uuid4(),
        name="Test Ad Project",
        status="ready",
        user_prompt="Focus on the 50% discount",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_brand_profile():
    """Create a sample brand profile for testing."""
    return BrandProfile(
        id=uuid.uuid4(),
        industry="Home Services",
        niche="Plumbing",
        core_offer="24/7 Emergency Plumbing",
        keywords=["fast", "reliable", "affordable"],
        tone="professional_friendly",
        forbidden_terms=["cheap", "budget"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_segments():
    """Create sample video segments for testing."""
    project_id = uuid.uuid4()
    file_id = uuid.uuid4()
    return [
        UserVideoSegment(
            id=uuid.uuid4(),
            project_id=project_id,
            source_file_id=file_id,
            source_file_name="demo_video.mp4",
            timestamp_start=0.0,
            timestamp_end=5.0,
            duration_seconds=5.0,
            visual_description="Close-up of hands installing a faucet",
            action_tags=["hands", "installation", "faucet", "close-up"],
            created_at=datetime.now(timezone.utc),
        ),
        UserVideoSegment(
            id=uuid.uuid4(),
            project_id=project_id,
            source_file_id=file_id,
            source_file_name="demo_video.mp4",
            timestamp_start=5.0,
            timestamp_end=12.0,
            duration_seconds=7.0,
            visual_description="Person smiling and showing the finished result",
            action_tags=["testimonial", "happy", "result", "success"],
            created_at=datetime.now(timezone.utc),
        ),
        UserVideoSegment(
            id=uuid.uuid4(),
            project_id=project_id,
            source_file_id=file_id,
            source_file_name="problem_clip.mp4",
            timestamp_start=0.0,
            timestamp_end=4.0,
            duration_seconds=4.0,
            visual_description="Water leaking from a broken faucet, frustrated homeowner",
            action_tags=["problem", "leak", "frustrated", "water"],
            created_at=datetime.now(timezone.utc),
        ),
    ]


class TestContentPlanningAgent:
    """Tests for ContentPlanningAgent class."""

    def test_init(self):
        """Test ContentPlanningAgent initialization."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()
            assert agent.model == "gpt-4-turbo-preview"

    def test_build_planning_input_basic(self, sample_recipe, sample_project, sample_segments):
        """Test building planning input from basic data."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()

            planning_input = agent._build_planning_input(
                recipe=sample_recipe,
                segments=sample_segments,
                project=sample_project,
                user_prompt="Test prompt",
            )

            assert planning_input.recipe_name == "Hook + PAS + CTA"
            assert planning_input.recipe_pacing == "fast"
            assert planning_input.recipe_style == "ugc"
            assert planning_input.total_target_duration == 20
            assert len(planning_input.recipe_structure) == 4
            assert len(planning_input.user_content_summaries) == 3
            assert planning_input.user_prompt == "Test prompt"
            assert planning_input.brand_profile is None  # No brand profile on project

    def test_build_planning_input_with_brand_profile(
        self, sample_recipe, sample_project, sample_brand_profile, sample_segments
    ):
        """Test building planning input with brand profile."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()

            # Attach brand profile to project
            sample_project.brand_profile = sample_brand_profile

            planning_input = agent._build_planning_input(
                recipe=sample_recipe,
                segments=sample_segments,
                project=sample_project,
                user_prompt=None,
            )

            assert planning_input.brand_profile is not None
            assert planning_input.brand_profile["industry"] == "Home Services"
            assert planning_input.brand_profile["tone"] == "professional_friendly"
            # Should fall back to project's user_prompt
            assert planning_input.user_prompt == "Focus on the 50% discount"

    def test_build_planning_input_empty_segments(self, sample_recipe, sample_project):
        """Test building planning input with no segments."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()

            planning_input = agent._build_planning_input(
                recipe=sample_recipe,
                segments=[],
                project=sample_project,
                user_prompt=None,
            )

            assert planning_input.user_content_summaries == []

    def test_parse_planning_output(self, mock_openai_response):
        """Test parsing LLM response into ContentPlanningOutput."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()

            output = agent._parse_planning_output(mock_openai_response)

            assert isinstance(output, ContentPlanningOutput)
            assert len(output.slots) == 4
            assert output.total_duration_seconds == 20
            assert output.audio_suggestion == "upbeat_trending"
            assert len(output.planning_notes) == 2

            # Check first slot
            hook_slot = output.slots[0]
            assert hook_slot.id == "slot_01_hook"
            assert hook_slot.beat_type == "Hook"
            assert hook_slot.target_duration == 3.0
            assert "energetic action" in hook_slot.search_query
            assert hook_slot.overlay_text == "Stop Wasting Money!"

    def test_parse_planning_output_missing_fields(self):
        """Test parsing output with missing optional fields."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()

            minimal_response = {
                "slots": [
                    {
                        "id": "slot_01",
                        "beat_type": "Hook",
                        "target_duration": 3.0,
                        "search_query": "test query",
                    }
                ],
                "total_duration_seconds": 3,
            }

            output = agent._parse_planning_output(minimal_response)

            assert len(output.slots) == 1
            assert output.slots[0].overlay_text is None
            assert output.slots[0].characteristics == []
            assert output.audio_suggestion is None

    @pytest.mark.asyncio
    async def test_generate_script_success(
        self, sample_recipe, sample_project, sample_segments, mock_openai_response
    ):
        """Test successful visual script generation."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()

            # Mock OpenAI response
            mock_completion = MagicMock()
            mock_completion.choices = [
                MagicMock(message=MagicMock(content=json.dumps(mock_openai_response)))
            ]
            agent.openai_client = AsyncMock()
            agent.openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

            planning_input = ContentPlanningInput(
                recipe_name="Test Recipe",
                recipe_structure=[{"beat_type": "Hook", "target_duration": 3.0}],
                recipe_pacing="fast",
                recipe_style="ugc",
                total_target_duration=20,
                user_content_summaries=["Test content"],
                user_prompt="Test prompt",
                brand_profile=None,
            )

            output = await agent._generate_script(planning_input)

            assert isinstance(output, ContentPlanningOutput)
            assert len(output.slots) == 4
            agent.openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_script_with_markdown_cleanup(self):
        """Test that markdown code blocks are properly cleaned from response."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()

            response_with_markdown = """```json
{
    "slots": [{"id": "slot_01", "beat_type": "Hook", "target_duration": 3.0, "search_query": "test"}],
    "total_duration_seconds": 3
}
```"""

            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock(message=MagicMock(content=response_with_markdown))]
            agent.openai_client = AsyncMock()
            agent.openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

            planning_input = ContentPlanningInput(
                recipe_name="Test",
                recipe_structure=[],
                recipe_pacing=None,
                recipe_style=None,
                total_target_duration=3,
                user_content_summaries=[],
                user_prompt=None,
                brand_profile=None,
            )

            output = await agent._generate_script(planning_input)
            assert len(output.slots) == 1

    @pytest.mark.asyncio
    async def test_generate_script_empty_response_error(self):
        """Test that empty LLM response raises error."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()

            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock(message=MagicMock(content=""))]
            agent.openai_client = AsyncMock()
            agent.openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

            planning_input = ContentPlanningInput(
                recipe_name="Test",
                recipe_structure=[],
                recipe_pacing=None,
                recipe_style=None,
                total_target_duration=3,
                user_content_summaries=[],
                user_prompt=None,
                brand_profile=None,
            )

            with pytest.raises(ContentPlanningError, match="Empty response"):
                await agent._generate_script(planning_input)

    @pytest.mark.asyncio
    async def test_generate_script_invalid_json_error(self):
        """Test that invalid JSON raises error."""
        with patch("app.services.content_planner.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key="test-key")
            agent = ContentPlanningAgent()

            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock(message=MagicMock(content="not valid json {"))]
            agent.openai_client = AsyncMock()
            agent.openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

            planning_input = ContentPlanningInput(
                recipe_name="Test",
                recipe_structure=[],
                recipe_pacing=None,
                recipe_style=None,
                total_target_duration=3,
                user_content_summaries=[],
                user_prompt=None,
                brand_profile=None,
            )

            with pytest.raises(ContentPlanningError, match="Failed to parse"):
                await agent._generate_script(planning_input)


class TestVisualScriptSlot:
    """Tests for VisualScriptSlot schema."""

    def test_slot_creation_full(self):
        """Test creating a slot with all fields."""
        slot = VisualScriptSlot(
            id="slot_01_hook",
            beat_type="Hook",
            target_duration=3.0,
            search_query="energetic action, surprise",
            overlay_text="Stop!",
            text_position="center",
            transition_in=None,
            transition_out="cut",
            notes="High energy needed",
            characteristics=["fast_cuts", "bold_text"],
            cinematics={"camera_angle": "close-up"},
        )

        assert slot.id == "slot_01_hook"
        assert slot.beat_type == "Hook"
        assert slot.target_duration == 3.0
        assert slot.overlay_text == "Stop!"

    def test_slot_creation_minimal(self):
        """Test creating a slot with minimal required fields."""
        slot = VisualScriptSlot(
            id="slot_01",
            beat_type="Hook",
            target_duration=3.0,
            search_query="test query",
        )

        assert slot.id == "slot_01"
        assert slot.overlay_text is None
        assert slot.characteristics == []
        assert slot.cinematics is None


class TestContentPlanningInput:
    """Tests for ContentPlanningInput schema."""

    def test_input_creation(self):
        """Test creating planning input."""
        input_data = ContentPlanningInput(
            recipe_name="Test Recipe",
            recipe_structure=[{"beat_type": "Hook"}],
            recipe_pacing="fast",
            recipe_style="ugc",
            total_target_duration=30,
            user_content_summaries=["Content 1", "Content 2"],
            user_prompt="Focus on discount",
            brand_profile={"industry": "Tech"},
        )

        assert input_data.recipe_name == "Test Recipe"
        assert len(input_data.user_content_summaries) == 2
        assert input_data.brand_profile["industry"] == "Tech"


class TestContentPlanningOutput:
    """Tests for ContentPlanningOutput schema."""

    def test_output_creation(self):
        """Test creating planning output."""
        slot = VisualScriptSlot(
            id="slot_01",
            beat_type="Hook",
            target_duration=3.0,
            search_query="test",
        )

        output = ContentPlanningOutput(
            slots=[slot],
            total_duration_seconds=30,
            audio_suggestion="upbeat",
            pacing_notes="Fast hook",
            planning_notes=["Note 1", "Note 2"],
        )

        assert len(output.slots) == 1
        assert output.total_duration_seconds == 30
        assert len(output.planning_notes) == 2

    def test_output_defaults(self):
        """Test output with default values."""
        slot = VisualScriptSlot(
            id="slot_01",
            beat_type="Hook",
            target_duration=3.0,
            search_query="test",
        )

        output = ContentPlanningOutput(
            slots=[slot],
            total_duration_seconds=30,
        )

        assert output.audio_suggestion is None
        assert output.planning_notes == []
