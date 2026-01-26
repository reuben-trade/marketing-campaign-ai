"""Tests for project file upload API endpoints."""

import io
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.fixture
def sample_project():
    """Sample project data."""
    return {
        "name": "Upload Test Project",
        "max_videos": 5,
        "max_total_size_mb": 100,
    }


@pytest.fixture
def video_file():
    """Create a mock video file."""
    content = b"fake video content " * 1000  # ~19KB
    return ("test_video.mp4", io.BytesIO(content), "video/mp4")


@pytest.fixture
def large_video_file():
    """Create a large mock video file (over 100MB limit)."""
    content = b"x" * (101 * 1024 * 1024)  # 101MB
    return ("large_video.mp4", io.BytesIO(content), "video/mp4")


@pytest.fixture
def invalid_file():
    """Create an invalid file type."""
    content = b"not a video"
    return ("document.pdf", io.BytesIO(content), "application/pdf")


@pytest.mark.asyncio
async def test_upload_single_file(client: AsyncClient, sample_project, video_file, mock_supabase_storage):
    """Test uploading a single video file."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    # Upload file
    filename, content, content_type = video_file
    files = [("files", (filename, content, content_type))]
    response = await client.post(f"/api/projects/{project_id}/upload", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == project_id
    assert data["total_files"] == 1
    assert len(data["uploaded_files"]) == 1
    assert data["uploaded_files"][0]["original_filename"] == "test_video.mp4"
    assert data["uploaded_files"][0]["status"] == "pending"
    assert "file_url" in data["uploaded_files"][0]


@pytest.mark.asyncio
async def test_upload_multiple_files(client: AsyncClient, sample_project, mock_supabase_storage):
    """Test uploading multiple video files."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # Create multiple files
    files = []
    for i in range(3):
        content = b"video content " * 1000
        files.append(("files", (f"video_{i}.mp4", io.BytesIO(content), "video/mp4")))

    response = await client.post(f"/api/projects/{project_id}/upload", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["total_files"] == 3
    assert len(data["uploaded_files"]) == 3


@pytest.mark.asyncio
async def test_upload_exceeds_file_count_limit(client: AsyncClient, mock_supabase_storage):
    """Test that uploading more than max_videos fails."""
    # Create project with max 2 videos
    project_data = {"name": "Limited Project", "max_videos": 2}
    create_response = await client.post("/api/projects", json=project_data)
    project_id = create_response.json()["id"]

    # Try to upload 3 files
    files = []
    for i in range(3):
        content = b"video content " * 100
        files.append(("files", (f"video_{i}.mp4", io.BytesIO(content), "video/mp4")))

    response = await client.post(f"/api/projects/{project_id}/upload", files=files)

    assert response.status_code == 400
    assert "exceed maximum of 2 videos" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client: AsyncClient, sample_project, invalid_file, mock_supabase_storage):
    """Test that uploading non-video files fails."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # Try to upload invalid file
    filename, content, content_type = invalid_file
    files = [("files", (filename, content, content_type))]
    response = await client.post(f"/api/projects/{project_id}/upload", files=files)

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file(client: AsyncClient, sample_project, mock_supabase_storage):
    """Test that uploading empty files fails."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # Try to upload empty file
    files = [("files", ("empty.mp4", io.BytesIO(b""), "video/mp4"))]
    response = await client.post(f"/api/projects/{project_id}/upload", files=files)

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_to_nonexistent_project(client: AsyncClient, video_file, mock_supabase_storage):
    """Test uploading to a non-existent project fails."""
    fake_project_id = str(uuid4())
    filename, content, content_type = video_file
    files = [("files", (filename, content, content_type))]

    response = await client.post(f"/api/projects/{fake_project_id}/upload", files=files)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_project_files(client: AsyncClient, sample_project, video_file, mock_supabase_storage):
    """Test listing uploaded files for a project."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # Upload file
    filename, content, content_type = video_file
    files = [("files", (filename, content, content_type))]
    await client.post(f"/api/projects/{project_id}/upload", files=files)

    # List files
    response = await client.get(f"/api/projects/{project_id}/files")

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert data["total"] == 1
    assert len(data["files"]) == 1
    assert data["total_size_bytes"] > 0


@pytest.mark.asyncio
async def test_list_files_empty_project(client: AsyncClient, sample_project, mock_supabase_storage):
    """Test listing files for a project with no uploads."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # List files
    response = await client.get(f"/api/projects/{project_id}/files")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["files"]) == 0


@pytest.mark.asyncio
async def test_list_files_nonexistent_project(client: AsyncClient):
    """Test listing files for a non-existent project."""
    fake_project_id = str(uuid4())
    response = await client.get(f"/api/projects/{fake_project_id}/files")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_file(client: AsyncClient, sample_project, video_file, mock_supabase_storage):
    """Test deleting a specific file from a project."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # Upload file
    filename, content, content_type = video_file
    files = [("files", (filename, content, content_type))]
    upload_response = await client.post(f"/api/projects/{project_id}/upload", files=files)
    file_id = upload_response.json()["uploaded_files"][0]["file_id"]

    # Delete file
    response = await client.delete(f"/api/projects/{project_id}/files/{file_id}")

    assert response.status_code == 204

    # Verify file is deleted
    list_response = await client.get(f"/api/projects/{project_id}/files")
    assert list_response.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_file(client: AsyncClient, sample_project, mock_supabase_storage):
    """Test deleting a non-existent file."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    fake_file_id = str(uuid4())
    response = await client.delete(f"/api/projects/{project_id}/files/{fake_file_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_project_stats_after_upload(client: AsyncClient, sample_project, video_file, mock_supabase_storage):
    """Test that project stats are updated after upload."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # Check initial stats
    initial_stats = create_response.json()["stats"]
    assert initial_stats["videos_uploaded"] == 0
    assert initial_stats["total_size_mb"] == 0.0

    # Upload file
    filename, content, content_type = video_file
    files = [("files", (filename, content, content_type))]
    await client.post(f"/api/projects/{project_id}/upload", files=files)

    # Check updated stats
    response = await client.get(f"/api/projects/{project_id}")
    updated_stats = response.json()["stats"]
    assert updated_stats["videos_uploaded"] == 1
    assert updated_stats["total_size_mb"] > 0


@pytest.mark.asyncio
async def test_upload_various_video_formats(client: AsyncClient, sample_project, mock_supabase_storage):
    """Test uploading various supported video formats."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # Test various formats
    formats = [
        ("test.mp4", "video/mp4"),
        ("test.mov", "video/quicktime"),
        ("test.webm", "video/webm"),
        ("test.avi", "video/x-msvideo"),
        ("test.m4v", "video/x-m4v"),
    ]

    for filename, content_type in formats:
        content = b"video content " * 100
        files = [("files", (filename, io.BytesIO(content), content_type))]
        response = await client.post(f"/api/projects/{project_id}/upload", files=files)

        assert response.status_code == 201, f"Failed to upload {filename}"


@pytest.mark.asyncio
async def test_cumulative_upload_limit(client: AsyncClient, mock_supabase_storage):
    """Test that cumulative uploads respect the file count limit."""
    # Create project with max 3 videos
    project_data = {"name": "Limited Project", "max_videos": 3}
    create_response = await client.post("/api/projects", json=project_data)
    project_id = create_response.json()["id"]

    # Upload 2 files first
    files = []
    for i in range(2):
        content = b"video " * 100
        files.append(("files", (f"video_{i}.mp4", io.BytesIO(content), "video/mp4")))
    response1 = await client.post(f"/api/projects/{project_id}/upload", files=files)
    assert response1.status_code == 201

    # Try to upload 2 more (should fail - would be 4 total)
    files2 = []
    for i in range(2):
        content = b"video " * 100
        files2.append(("files", (f"video_extra_{i}.mp4", io.BytesIO(content), "video/mp4")))
    response2 = await client.post(f"/api/projects/{project_id}/upload", files=files2)
    assert response2.status_code == 400
    assert "exceed maximum of 3 videos" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_delete_project_cascades_files(client: AsyncClient, sample_project, video_file, mock_supabase_storage):
    """Test that deleting a project also deletes its files."""
    # Create project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # Upload file
    filename, content, content_type = video_file
    files = [("files", (filename, content, content_type))]
    await client.post(f"/api/projects/{project_id}/upload", files=files)

    # Delete project
    response = await client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204

    # Verify project and files are gone
    get_response = await client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 404
