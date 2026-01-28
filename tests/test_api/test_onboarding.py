"""Tests for the onboarding API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_profile import BrandProfile


@pytest.fixture
async def sample_brand_profile(db_session: AsyncSession) -> BrandProfile:
    """Create a sample brand profile for testing."""
    profile = BrandProfile(
        industry="ecommerce",
        niche="Fashion",
        core_offer="Premium sustainable clothing for conscious consumers",
        competitors=["550e8400-e29b-41d4-a716-446655440001"],
        keywords=["sustainable", "premium", "fashion", "eco-friendly"],
        tone="professional_friendly",
        forbidden_terms=["cheap", "discount"],
        logo_url="https://example.com/logo.png",
        primary_color="#FF5733",
        font_family="Inter",
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


class TestOnboardingStatus:
    """Tests for onboarding status endpoint."""

    async def test_status_no_profile(self, client: AsyncClient) -> None:
        """Test status when no brand profile exists."""
        response = await client.get("/api/onboarding/status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_brand_profile"] is False
        assert data["brand_profile"] is None
        assert data["completed_steps"] == 0

    async def test_status_with_profile(
        self, client: AsyncClient, sample_brand_profile: BrandProfile
    ) -> None:
        """Test status when brand profile exists."""
        response = await client.get("/api/onboarding/status")
        assert response.status_code == 200
        data = response.json()
        assert data["has_brand_profile"] is True
        assert data["brand_profile"] is not None
        assert data["brand_profile"]["industry"] == "ecommerce"
        assert data["completed_steps"] == 3


class TestCompleteOnboarding:
    """Tests for completing onboarding."""

    async def test_complete_onboarding_minimal(self, client: AsyncClient) -> None:
        """Test completing onboarding with minimal required fields."""
        payload = {
            "industry": "saas",
            "core_offer": "AI-powered analytics dashboard for small businesses",
        }
        response = await client.post("/api/onboarding", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["industry"] == "saas"
        assert data["core_offer"] == payload["core_offer"]
        assert data["id"] is not None

    async def test_complete_onboarding_full(self, client: AsyncClient) -> None:
        """Test completing onboarding with all fields."""
        payload = {
            "industry": "health_fitness",
            "niche": "Personal Training",
            "core_offer": "Online personal training programs with 1-on-1 coaching",
            "keywords": ["fitness", "personal trainer", "weight loss", "muscle gain"],
            "tone": "inspirational",
            "competitors": ["550e8400-e29b-41d4-a716-446655440001"],
            "forbidden_terms": ["steroids", "quick fix"],
            "logo_url": "https://example.com/fitness-logo.png",
            "primary_color": "#00FF00",
            "font_family": "Roboto",
        }
        response = await client.post("/api/onboarding", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["industry"] == "health_fitness"
        assert data["niche"] == "Personal Training"
        assert data["keywords"] == payload["keywords"]
        assert data["tone"] == "inspirational"
        assert data["primary_color"] == "#00FF00"

    async def test_complete_onboarding_invalid_industry(self, client: AsyncClient) -> None:
        """Test validation for empty industry."""
        payload = {
            "industry": "",
            "core_offer": "Some offer",
        }
        response = await client.post("/api/onboarding", json=payload)
        assert response.status_code == 422

    async def test_complete_onboarding_short_core_offer(self, client: AsyncClient) -> None:
        """Test validation for short core offer."""
        payload = {
            "industry": "saas",
            "core_offer": "Short",  # Less than 10 characters
        }
        response = await client.post("/api/onboarding", json=payload)
        assert response.status_code == 422

    async def test_complete_onboarding_invalid_color(self, client: AsyncClient) -> None:
        """Test validation for invalid color format."""
        payload = {
            "industry": "saas",
            "core_offer": "AI-powered analytics dashboard",
            "primary_color": "not-a-color",  # Invalid hex color
        }
        response = await client.post("/api/onboarding", json=payload)
        assert response.status_code == 422


class TestGetBrandProfile:
    """Tests for getting brand profile."""

    async def test_get_brand_profile_not_found(self, client: AsyncClient) -> None:
        """Test getting brand profile when none exists."""
        response = await client.get("/api/onboarding")
        assert response.status_code == 404

    async def test_get_brand_profile(
        self, client: AsyncClient, sample_brand_profile: BrandProfile
    ) -> None:
        """Test getting the current brand profile."""
        response = await client.get("/api/onboarding")
        assert response.status_code == 200
        data = response.json()
        assert data["industry"] == "ecommerce"
        assert data["niche"] == "Fashion"

    async def test_get_brand_profile_by_id(
        self, client: AsyncClient, sample_brand_profile: BrandProfile
    ) -> None:
        """Test getting brand profile by ID."""
        response = await client.get(f"/api/onboarding/{sample_brand_profile.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_brand_profile.id)

    async def test_get_brand_profile_by_id_not_found(self, client: AsyncClient) -> None:
        """Test getting non-existent brand profile."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await client.get(f"/api/onboarding/{fake_id}")
        assert response.status_code == 404


class TestUpdateBrandProfile:
    """Tests for updating brand profile."""

    async def test_update_brand_profile(
        self, client: AsyncClient, sample_brand_profile: BrandProfile
    ) -> None:
        """Test updating a brand profile."""
        payload = {
            "niche": "Luxury Fashion",
            "tone": "luxurious",
        }
        response = await client.put(f"/api/onboarding/{sample_brand_profile.id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["niche"] == "Luxury Fashion"
        assert data["tone"] == "luxurious"
        # Original fields should be preserved
        assert data["industry"] == "ecommerce"

    async def test_update_brand_profile_not_found(self, client: AsyncClient) -> None:
        """Test updating non-existent brand profile."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        payload = {"niche": "New Niche"}
        response = await client.put(f"/api/onboarding/{fake_id}", json=payload)
        assert response.status_code == 404


class TestDeleteBrandProfile:
    """Tests for deleting brand profile."""

    async def test_delete_brand_profile(
        self, client: AsyncClient, sample_brand_profile: BrandProfile
    ) -> None:
        """Test deleting a brand profile."""
        response = await client.delete(f"/api/onboarding/{sample_brand_profile.id}")
        assert response.status_code == 204

        # Verify it's deleted
        response = await client.get(f"/api/onboarding/{sample_brand_profile.id}")
        assert response.status_code == 404

    async def test_delete_brand_profile_not_found(self, client: AsyncClient) -> None:
        """Test deleting non-existent brand profile."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await client.delete(f"/api/onboarding/{fake_id}")
        assert response.status_code == 404


class TestListBrandProfiles:
    """Tests for listing brand profiles."""

    async def test_list_brand_profiles_empty(self, client: AsyncClient) -> None:
        """Test listing when no profiles exist."""
        response = await client.get("/api/onboarding/all")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_brand_profiles(
        self, client: AsyncClient, sample_brand_profile: BrandProfile
    ) -> None:
        """Test listing brand profiles."""
        response = await client.get("/api/onboarding/all")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(sample_brand_profile.id)


class TestOptions:
    """Tests for options endpoints."""

    async def test_get_industry_options(self, client: AsyncClient) -> None:
        """Test getting industry options."""
        response = await client.get("/api/onboarding/options/industries")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(opt["value"] == "ecommerce" for opt in data)
        assert any(opt["value"] == "saas" for opt in data)

    async def test_get_tone_options(self, client: AsyncClient) -> None:
        """Test getting tone options."""
        response = await client.get("/api/onboarding/options/tones")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(opt["value"] == "professional_friendly" for opt in data)
        assert any(opt["value"] == "casual" for opt in data)
