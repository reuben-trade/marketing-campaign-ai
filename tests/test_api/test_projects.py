"""Tests for projects API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.fixture
def sample_project():
    """Sample project data."""
    return {
        "name": "Summer Sale Campaign",
        "user_prompt": "Focus on the 50% discount, show product in use",
    }


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, sample_project):
    """Test creating a project."""
    response = await client.post("/api/projects", json=sample_project)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_project["name"]
    assert data["user_prompt"] == sample_project["user_prompt"]
    assert data["status"] == "draft"
    assert data["max_videos"] == 10
    assert data["max_total_size_mb"] == 500
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "stats" in data


@pytest.mark.asyncio
async def test_create_project_with_constraints(client: AsyncClient):
    """Test creating a project with custom constraints."""
    project_data = {
        "name": "Custom Project",
        "max_videos": 5,
        "max_total_size_mb": 250,
    }
    response = await client.post("/api/projects", json=project_data)

    assert response.status_code == 201
    data = response.json()
    assert data["max_videos"] == 5
    assert data["max_total_size_mb"] == 250


@pytest.mark.asyncio
async def test_create_project_minimal(client: AsyncClient):
    """Test creating a project with minimal data."""
    project_data = {"name": "Minimal Project"}
    response = await client.post("/api/projects", json=project_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Project"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_create_project_missing_name(client: AsyncClient):
    """Test creating a project without name fails."""
    response = await client.post("/api/projects", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, sample_project):
    """Test getting a project by ID."""
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    response = await client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == sample_project["name"]


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient):
    """Test getting a non-existent project."""
    response = await client.get("/api/projects/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, sample_project):
    """Test updating a project."""
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    update_data = {"name": "Updated Campaign Name"}
    response = await client.put(f"/api/projects/{project_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Campaign Name"
    # Original prompt should remain unchanged
    assert data["user_prompt"] == sample_project["user_prompt"]


@pytest.mark.asyncio
async def test_update_project_status(client: AsyncClient, sample_project):
    """Test updating project status."""
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    update_data = {"status": "processing"}
    response = await client.put(f"/api/projects/{project_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_update_project_invalid_status(client: AsyncClient, sample_project):
    """Test updating project with invalid status."""
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    update_data = {"status": "invalid_status"}
    response = await client.put(f"/api/projects/{project_id}", json=update_data)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_project_not_found(client: AsyncClient):
    """Test updating a non-existent project."""
    response = await client.put(
        "/api/projects/00000000-0000-0000-0000-000000000000",
        json={"name": "Updated"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, sample_project):
    """Test deleting a project."""
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    response = await client.delete(f"/api/projects/{project_id}")

    assert response.status_code == 204

    # Verify it's deleted
    get_response = await client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_not_found(client: AsyncClient):
    """Test deleting a non-existent project."""
    response = await client.delete("/api/projects/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, sample_project):
    """Test listing projects."""
    # Create multiple projects
    await client.post("/api/projects", json=sample_project)
    await client.post("/api/projects", json={"name": "Another Project"})

    response = await client.get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_list_projects_pagination(client: AsyncClient, sample_project):
    """Test project listing with pagination."""
    # Create 5 projects
    for i in range(5):
        await client.post("/api/projects", json={"name": f"Project {i}"})

    response = await client.get("/api/projects?page=1&page_size=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total"] >= 5


@pytest.mark.asyncio
async def test_list_projects_filter_by_status(client: AsyncClient, sample_project):
    """Test filtering projects by status."""
    # Create a draft project
    create_response = await client.post("/api/projects", json=sample_project)
    project_id = create_response.json()["id"]

    # Update to processing
    await client.put(f"/api/projects/{project_id}", json={"status": "processing"})

    # Create another draft project
    await client.post("/api/projects", json={"name": "Draft Project"})

    # Filter by processing
    response = await client.get("/api/projects?status=processing")

    assert response.status_code == 200
    data = response.json()
    assert all(p["status"] == "processing" for p in data["items"])


@pytest.mark.asyncio
async def test_list_projects_invalid_status_filter(client: AsyncClient):
    """Test filtering by invalid status."""
    response = await client.get("/api/projects?status=invalid")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_project_stats_initial(client: AsyncClient, sample_project):
    """Test that new projects have zero stats."""
    response = await client.post("/api/projects", json=sample_project)

    assert response.status_code == 201
    data = response.json()
    assert data["stats"]["videos_uploaded"] == 0
    assert data["stats"]["total_size_mb"] == 0.0
    assert data["stats"]["segments_extracted"] == 0


@pytest.mark.asyncio
async def test_create_project_with_inspiration_ads(client: AsyncClient):
    """Test creating a project with inspiration ads."""
    project_data = {
        "name": "Inspired Project",
        "inspiration_ads": [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        ],
    }
    response = await client.post("/api/projects", json=project_data)

    assert response.status_code == 201
    data = response.json()
    assert data["inspiration_ads"] is not None
    assert len(data["inspiration_ads"]) == 2
