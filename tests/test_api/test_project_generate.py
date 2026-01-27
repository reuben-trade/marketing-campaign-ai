"""Tests for project ad generation endpoint."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.fixture
def sample_project():
    """Sample project data."""
    return {
        "name": "Generation Test Project",
        "user_prompt": "Focus on the 50% discount",
    }


@pytest.fixture
def sample_recipe_id():
    """Sample recipe ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_content_planner():
    """Mock ContentPlanningAgent for testing."""
    with patch("app.api.projects.ContentPlanningAgent") as mock:
        mock_instance = MagicMock()
        mock_instance.generate = AsyncMock(
            return_value=MagicMock(
                id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                recipe_id=uuid.uuid4(),
                total_duration_seconds=30,
                slots=[
                    MagicMock(
                        id="slot_01_hook",
                        beat_type="Hook",
                        target_duration=3.0,
                        search_query="energetic action",
                        overlay_text="Stop!",
                    ),
                    MagicMock(
                        id="slot_02_problem",
                        beat_type="Problem",
                        target_duration=5.0,
                        search_query="frustrated expression",
                        overlay_text="Tired of this?",
                    ),
                ],
                audio_suggestion="upbeat",
                pacing_notes="Fast cuts",
                created_at=MagicMock(),
                updated_at=MagicMock(),
            )
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_director_agent():
    """Mock DirectorAgent for testing."""
    with patch("app.api.projects.DirectorAgent") as mock:
        mock_instance = MagicMock()
        mock_instance.assemble = AsyncMock(
            return_value=MagicMock(
                payload=MagicMock(
                    composition_id=MagicMock(value="vertical_ad_v1"),
                    width=1080,
                    height=1920,
                    fps=30,
                    duration_in_frames=900,
                    timeline=[
                        MagicMock(
                            id="segment_01",
                            type=MagicMock(value="video_clip"),
                            beat_type="Hook",
                            duration_frames=90,
                            overlay=MagicMock(text="Stop!"),
                            similarity_score=0.85,
                        ),
                        MagicMock(
                            id="segment_02",
                            type=MagicMock(value="video_clip"),
                            beat_type="Problem",
                            duration_frames=150,
                            overlay=None,
                            similarity_score=0.72,
                        ),
                    ],
                    audio_track=None,
                    brand_profile=None,
                    gaps=None,
                    warnings=None,
                ),
                stats={
                    "total_slots": 2,
                    "clips_selected": 2,
                    "gaps_detected": 0,
                    "coverage_percentage": 100.0,
                    "average_similarity": 0.785,
                    "total_duration_seconds": 30.0,
                    "total_frames": 900,
                },
                success=True,
                error_message=None,
            )
        )
        mock.return_value = mock_instance
        yield mock_instance


async def _create_project_with_segments(client: AsyncClient, db_session, sample_project):
    """Helper to create a project with mock segments."""
    from app.models.user_video_segment import UserVideoSegment

    # Create project
    response = await client.post("/api/projects", json=sample_project)
    project_data = response.json()
    project_id = uuid.UUID(project_data["id"])

    # Add segments directly to database
    segment = UserVideoSegment(
        id=uuid.uuid4(),
        project_id=project_id,
        source_file_id=uuid.uuid4(),
        source_file_name="test_video.mp4",
        source_file_url="https://test.com/video.mp4",
        timestamp_start=0.0,
        timestamp_end=5.0,
        duration_seconds=5.0,
        visual_description="Test segment with action",
        action_tags=["action", "test"],
    )
    db_session.add(segment)
    await db_session.commit()

    return project_id


@pytest.mark.asyncio
async def test_generate_ad_success(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test successful ad generation."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "user_prompt": "Focus on the discount",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == str(project_id)
    assert "visual_script_id" in data
    assert "payload_preview" in data
    assert "stats" in data
    assert data["success"] is True


@pytest.mark.asyncio
async def test_generate_ad_response_structure(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test the structure of the generation response."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={"recipe_id": sample_recipe_id},
    )

    assert response.status_code == 200
    data = response.json()

    # Check stats structure
    stats = data["stats"]
    assert "total_slots" in stats
    assert "clips_selected" in stats
    assert "gaps_detected" in stats
    assert "coverage_percentage" in stats
    assert "average_similarity" in stats
    assert "total_duration_seconds" in stats

    # Check payload preview structure
    preview = data["payload_preview"]
    assert "composition_id" in preview
    assert "width" in preview
    assert "height" in preview
    assert "fps" in preview
    assert "duration_in_frames" in preview
    assert "duration_seconds" in preview
    assert "timeline_segments" in preview
    assert "timeline_preview" in preview


@pytest.mark.asyncio
async def test_generate_ad_with_all_options(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test ad generation with all optional parameters."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "user_prompt": "Focus on urgency and FOMO",
            "composition_type": "horizontal_ad_v1",
            "min_similarity_threshold": 0.7,
            "gap_handling": "text_slide",
            "audio_url": "https://example.com/audio.mp3",
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_ad_project_not_found(client: AsyncClient):
    """Test generation with non-existent project."""
    fake_project_id = str(uuid.uuid4())
    fake_recipe_id = str(uuid.uuid4())

    response = await client.post(
        f"/api/projects/{fake_project_id}/generate",
        json={"recipe_id": fake_recipe_id},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_ad_no_segments(client: AsyncClient, sample_project):
    """Test generation fails when project has no analyzed segments."""
    # Create project without segments
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]
    recipe_id = str(uuid.uuid4())

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={"recipe_id": recipe_id},
    )

    assert response.status_code == 422
    assert "no analyzed video segments" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_ad_invalid_composition_type(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
):
    """Test generation with invalid composition type."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "composition_type": "invalid_type",
        },
    )

    assert response.status_code == 400
    assert "composition_type" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_ad_invalid_gap_handling(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
):
    """Test generation with invalid gap handling option."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "gap_handling": "invalid_option",
        },
    )

    assert response.status_code == 400
    assert "gap_handling" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_ad_vertical_composition(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test generation with vertical composition (default)."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "composition_type": "vertical_ad_v1",
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_ad_square_composition(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test generation with square composition."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "composition_type": "square_ad_v1",
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_ad_gap_handling_broll(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test generation with B-Roll gap handling."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "gap_handling": "broll",
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_ad_gap_handling_text_slide(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test generation with text slide gap handling."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "gap_handling": "text_slide",
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_ad_gap_handling_skip(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test generation with skip gap handling."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "gap_handling": "skip",
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_ad_updates_project_status(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test that generation updates project status to ready."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    # Verify initial status
    get_response = await client.get(f"/api/projects/{project_id}")
    assert get_response.json()["status"] == "draft"

    # Generate ad
    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={"recipe_id": sample_recipe_id},
    )
    assert response.status_code == 200

    # Verify status updated
    get_response = await client.get(f"/api/projects/{project_id}")
    assert get_response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_generate_ad_content_planner_failure(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
):
    """Test handling of content planner failure."""
    from app.services.content_planner import ContentPlanningError

    project_id = await _create_project_with_segments(client, db_session, sample_project)

    with patch("app.api.projects.ContentPlanningAgent") as mock:
        mock_instance = MagicMock()
        mock_instance.generate = AsyncMock(side_effect=ContentPlanningError("Recipe not found"))
        mock.return_value = mock_instance

        response = await client.post(
            f"/api/projects/{project_id}/generate",
            json={"recipe_id": sample_recipe_id},
        )

        assert response.status_code == 500
        assert "visual script" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_ad_director_failure(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
):
    """Test handling of director agent failure."""
    from app.services.director_agent import DirectorAgentError

    project_id = await _create_project_with_segments(client, db_session, sample_project)

    with patch("app.api.projects.DirectorAgent") as mock:
        mock_instance = MagicMock()
        mock_instance.assemble = AsyncMock(side_effect=DirectorAgentError("Assembly failed"))
        mock.return_value = mock_instance

        response = await client.post(
            f"/api/projects/{project_id}/generate",
            json={"recipe_id": sample_recipe_id},
        )

        assert response.status_code == 500
        assert "assemble" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_ad_similarity_threshold(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
    mock_director_agent,
):
    """Test generation with custom similarity threshold."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    # Test with high threshold
    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "min_similarity_threshold": 0.9,
        },
    )
    assert response.status_code == 200

    # Test with low threshold
    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "min_similarity_threshold": 0.1,
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_ad_invalid_similarity_threshold(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
):
    """Test generation with invalid similarity threshold."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    # Test with threshold above 1.0
    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "min_similarity_threshold": 1.5,
        },
    )
    assert response.status_code == 422  # Pydantic validation error

    # Test with negative threshold
    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={
            "recipe_id": sample_recipe_id,
            "min_similarity_threshold": -0.5,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_ad_missing_recipe_id(client: AsyncClient, db_session, sample_project):
    """Test generation fails without recipe_id."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    response = await client.post(
        f"/api/projects/{project_id}/generate",
        json={},
    )

    assert response.status_code == 422  # Pydantic validation requires recipe_id


@pytest.mark.asyncio
async def test_generate_ad_with_gaps(
    client: AsyncClient,
    db_session,
    sample_project,
    sample_recipe_id,
    mock_content_planner,
):
    """Test generation response includes gaps when clips not found."""
    project_id = await _create_project_with_segments(client, db_session, sample_project)

    with patch("app.api.projects.DirectorAgent") as mock:
        mock_instance = MagicMock()
        mock_instance.assemble = AsyncMock(
            return_value=MagicMock(
                payload=MagicMock(
                    composition_id=MagicMock(value="vertical_ad_v1"),
                    width=1080,
                    height=1920,
                    fps=30,
                    duration_in_frames=900,
                    timeline=[
                        MagicMock(
                            id="segment_01",
                            type=MagicMock(value="video_clip"),
                            beat_type="Hook",
                            duration_frames=90,
                            overlay=None,
                            similarity_score=0.85,
                        ),
                        MagicMock(
                            id="segment_02_broll",
                            type=MagicMock(value="generated_broll"),
                            beat_type="Problem",
                            duration_frames=150,
                            overlay=None,
                            similarity_score=None,
                        ),
                    ],
                    audio_track=None,
                    brand_profile=None,
                    gaps=[
                        {
                            "slot_id": "slot_02_problem",
                            "beat_type": "Problem",
                            "reason": "No matching clip found",
                            "search_query": "frustrated expression",
                            "handling": "broll",
                        }
                    ],
                    warnings=["Duration mismatch on slot_01_hook"],
                ),
                stats={
                    "total_slots": 2,
                    "clips_selected": 1,
                    "gaps_detected": 1,
                    "coverage_percentage": 50.0,
                    "average_similarity": 0.85,
                    "total_duration_seconds": 30.0,
                    "total_frames": 900,
                },
                success=True,
                error_message=None,
            )
        )
        mock.return_value = mock_instance

        response = await client.post(
            f"/api/projects/{project_id}/generate",
            json={"recipe_id": sample_recipe_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["gaps"] is not None
        assert len(data["gaps"]) == 1
        assert data["warnings"] is not None
        assert len(data["warnings"]) == 1
        assert data["stats"]["gaps_detected"] == 1
        assert data["stats"]["coverage_percentage"] == 50.0
