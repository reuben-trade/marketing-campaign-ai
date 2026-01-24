"""Tests for competitors API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_competitor(client: AsyncClient, sample_competitor):
    """Test adding a competitor."""
    response = await client.post("/api/competitors/add", json=sample_competitor)

    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == sample_competitor["company_name"]
    assert data["page_id"] == sample_competitor["page_id"]
    assert "id" in data


@pytest.mark.asyncio
async def test_add_duplicate_competitor(client: AsyncClient, sample_competitor):
    """Test adding a duplicate competitor."""
    await client.post("/api/competitors/add", json=sample_competitor)
    response = await client.post("/api/competitors/add", json=sample_competitor)

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_competitor(client: AsyncClient, sample_competitor):
    """Test getting a competitor by ID."""
    create_response = await client.post("/api/competitors/add", json=sample_competitor)
    competitor_id = create_response.json()["id"]

    response = await client.get(f"/api/competitors/{competitor_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == competitor_id
    assert data["company_name"] == sample_competitor["company_name"]


@pytest.mark.asyncio
async def test_get_competitor_not_found(client: AsyncClient):
    """Test getting a non-existent competitor."""
    response = await client.get("/api/competitors/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_competitor(client: AsyncClient, sample_competitor):
    """Test updating a competitor."""
    create_response = await client.post("/api/competitors/add", json=sample_competitor)
    competitor_id = create_response.json()["id"]

    update_data = {"company_name": "Updated Competitor Name"}
    response = await client.put(f"/api/competitors/{competitor_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "Updated Competitor Name"


@pytest.mark.asyncio
async def test_deactivate_competitor(client: AsyncClient, sample_competitor):
    """Test deactivating a competitor."""
    create_response = await client.post("/api/competitors/add", json=sample_competitor)
    competitor_id = create_response.json()["id"]

    response = await client.delete(f"/api/competitors/{competitor_id}")

    assert response.status_code == 204

    get_response = await client.get(f"/api/competitors/{competitor_id}")
    assert get_response.status_code == 200
    assert get_response.json()["active"] is False


@pytest.mark.asyncio
async def test_list_competitors(client: AsyncClient, sample_competitor):
    """Test listing competitors."""
    await client.post("/api/competitors/add", json=sample_competitor)
    await client.post(
        "/api/competitors/add",
        json={
            **sample_competitor,
            "company_name": "Another Competitor",
            "page_id": "987654321",
        },
    )

    response = await client.get("/api/competitors")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_list_competitors_pagination(client: AsyncClient, sample_competitor):
    """Test competitor listing with pagination."""
    for i in range(5):
        await client.post(
            "/api/competitors/add",
            json={
                **sample_competitor,
                "company_name": f"Competitor {i}",
                "page_id": f"{100000000 + i}",
            },
        )

    response = await client.get("/api/competitors?page=1&page_size=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
