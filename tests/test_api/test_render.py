"""Tests for render API callback authentication."""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_render_callback_valid_secret(client: AsyncClient):
    """Test callback with valid secret passes authentication."""
    render_id = uuid.uuid4()
    payload = {
        "render_id": str(render_id),
        "status": "completed",
        "video_url": "https://example.com/video.mp4",
    }

    with patch("app.api.render.get_settings") as mock_settings:
        mock_settings.return_value.render_callback_secret = "test-secret-123"

        response = await client.post(
            "/api/render/callback",
            json=payload,
            headers={"X-Render-Callback-Secret": "test-secret-123"},
        )

    # Should pass auth but return 404 since render doesn't exist
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_render_callback_invalid_secret(client: AsyncClient):
    """Test callback with invalid secret returns 401."""
    render_id = uuid.uuid4()
    payload = {
        "render_id": str(render_id),
        "status": "completed",
    }

    with patch("app.api.render.get_settings") as mock_settings:
        mock_settings.return_value.render_callback_secret = "correct-secret"

        response = await client.post(
            "/api/render/callback",
            json=payload,
            headers={"X-Render-Callback-Secret": "wrong-secret"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid callback secret"


@pytest.mark.asyncio
async def test_render_callback_missing_secret_header(client: AsyncClient):
    """Test callback without secret header returns 401."""
    render_id = uuid.uuid4()
    payload = {
        "render_id": str(render_id),
        "status": "completed",
    }

    with patch("app.api.render.get_settings") as mock_settings:
        mock_settings.return_value.render_callback_secret = "some-secret"

        response = await client.post(
            "/api/render/callback",
            json=payload,
            # No X-Render-Callback-Secret header
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid callback secret"


@pytest.mark.asyncio
async def test_render_callback_secret_not_configured(client: AsyncClient):
    """Test callback returns 503 when secret not configured."""
    render_id = uuid.uuid4()
    payload = {
        "render_id": str(render_id),
        "status": "completed",
    }

    with patch("app.api.render.get_settings") as mock_settings:
        mock_settings.return_value.render_callback_secret = ""

        response = await client.post(
            "/api/render/callback",
            json=payload,
            headers={"X-Render-Callback-Secret": "any-secret"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Render callback secret not configured"
