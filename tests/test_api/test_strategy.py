"""Tests for strategy API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_strategy(client: AsyncClient, sample_business_strategy):
    """Test creating a business strategy."""
    response = await client.post("/api/strategy", json=sample_business_strategy)

    assert response.status_code == 200
    data = response.json()
    assert data["business_name"] == sample_business_strategy["business_name"]
    assert data["industry"] == sample_business_strategy["industry"]
    assert "id" in data


@pytest.mark.asyncio
async def test_get_strategy(client: AsyncClient, sample_business_strategy):
    """Test getting a business strategy by ID."""
    create_response = await client.post("/api/strategy", json=sample_business_strategy)
    strategy_id = create_response.json()["id"]

    response = await client.get(f"/api/strategy/{strategy_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == strategy_id
    assert data["business_name"] == sample_business_strategy["business_name"]


@pytest.mark.asyncio
async def test_get_strategy_not_found(client: AsyncClient):
    """Test getting a non-existent strategy."""
    response = await client.get("/api/strategy/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_strategy(client: AsyncClient, sample_business_strategy):
    """Test updating a business strategy."""
    create_response = await client.post("/api/strategy", json=sample_business_strategy)
    strategy_id = create_response.json()["id"]

    update_data = {"business_name": "Updated Company Name"}
    response = await client.put(f"/api/strategy/{strategy_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["business_name"] == "Updated Company Name"


@pytest.mark.asyncio
async def test_delete_strategy(client: AsyncClient, sample_business_strategy):
    """Test deleting a business strategy."""
    create_response = await client.post("/api/strategy", json=sample_business_strategy)
    strategy_id = create_response.json()["id"]

    response = await client.delete(f"/api/strategy/{strategy_id}")

    assert response.status_code == 204

    get_response = await client.get(f"/api/strategy/{strategy_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_list_strategies(client: AsyncClient, sample_business_strategy):
    """Test listing all strategies."""
    await client.post("/api/strategy", json=sample_business_strategy)
    await client.post(
        "/api/strategy",
        json={**sample_business_strategy, "business_name": "Another Company"},
    )

    response = await client.get("/api/strategy")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
