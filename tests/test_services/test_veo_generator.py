"""Tests for the Veo 2 B-Roll generator service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generated_broll import GeneratedBRoll, GeneratedBRollClip
from app.schemas.veo_request import (
    PromptEnhancementRequest,
    VeoAspectRatio,
    VeoGenerateRequest,
    VeoGenerationStatus,
    VeoRegenerateRequest,
    VeoStyle,
)
from app.services.veo_generator import VeoGeneratorService


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def veo_service(mock_db: AsyncMock) -> VeoGeneratorService:
    """Create a Veo generator service with mock dependencies."""
    service = VeoGeneratorService(mock_db)
    service.storage = MagicMock()
    return service


@pytest.fixture
def sample_generate_request() -> VeoGenerateRequest:
    """Create a sample generation request."""
    return VeoGenerateRequest(
        prompt="Close-up of water splashing in slow motion, crystal clear water",
        duration_seconds=3.0,
        aspect_ratio=VeoAspectRatio.VERTICAL,
        style=VeoStyle.CINEMATIC,
        num_variants=2,
        project_id=uuid.uuid4(),
        slot_id="slot_01_hook",
    )


@pytest.fixture
def sample_generation() -> GeneratedBRoll:
    """Create a sample generation record."""
    return GeneratedBRoll(
        id=uuid.uuid4(),
        prompt="Close-up of water splashing in slow motion",
        duration_seconds=3.0,
        aspect_ratio="9:16",
        style="cinematic",
        num_variants=2,
        project_id=uuid.uuid4(),
        slot_id="slot_01_hook",
        status="pending",
        created_at=datetime.now(timezone.utc),
    )


class TestVeoGeneratorService:
    """Tests for VeoGeneratorService."""

    async def test_generate_broll_creates_job(
        self,
        veo_service: VeoGeneratorService,
        sample_generate_request: VeoGenerateRequest,
    ) -> None:
        """Test that generate_broll creates a generation job."""

        # Mock the database refresh to set ID
        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)

        veo_service.db.refresh = mock_refresh

        response = await veo_service.generate_broll(sample_generate_request)

        assert response.status == VeoGenerationStatus.PENDING
        assert response.prompt == sample_generate_request.prompt
        assert response.duration_seconds == sample_generate_request.duration_seconds
        assert response.aspect_ratio == sample_generate_request.aspect_ratio
        assert response.style == sample_generate_request.style
        assert response.num_variants == sample_generate_request.num_variants
        assert response.project_id == sample_generate_request.project_id
        assert response.slot_id == sample_generate_request.slot_id
        assert len(response.clips) == 0

        # Verify database operations
        veo_service.db.add.assert_called_once()
        assert veo_service.db.commit.call_count == 1

    async def test_generate_broll_with_negative_prompt(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test generation with negative prompt."""
        request = VeoGenerateRequest(
            prompt="Professional business meeting scene",
            duration_seconds=5.0,
            aspect_ratio=VeoAspectRatio.HORIZONTAL,
            style=VeoStyle.REALISTIC,
            num_variants=1,
            negative_prompt="blurry, low quality, cartoon",
        )

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)

        veo_service.db.refresh = mock_refresh

        response = await veo_service.generate_broll(request)

        assert response.status == VeoGenerationStatus.PENDING
        assert response.prompt == request.prompt

    async def test_get_generation_not_found(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test get_generation returns None for non-existent ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        veo_service.db.execute = AsyncMock(return_value=mock_result)

        result = await veo_service.get_generation(uuid.uuid4())

        assert result is None

    async def test_get_generation_with_clips(
        self,
        veo_service: VeoGeneratorService,
        sample_generation: GeneratedBRoll,
    ) -> None:
        """Test get_generation returns generation with clips."""
        generation_id = sample_generation.id
        sample_generation.status = "completed"

        # Create sample clips
        clips = [
            GeneratedBRollClip(
                id=uuid.uuid4(),
                generation_id=generation_id,
                url="https://storage.example.com/clip1.mp4",
                thumbnail_url="https://storage.example.com/thumb1.jpg",
                duration_seconds=3.0,
                width=1080,
                height=1920,
                file_size_bytes=1024000,
                variant_index=0,
            ),
            GeneratedBRollClip(
                id=uuid.uuid4(),
                generation_id=generation_id,
                url="https://storage.example.com/clip2.mp4",
                thumbnail_url="https://storage.example.com/thumb2.jpg",
                duration_seconds=3.0,
                width=1080,
                height=1920,
                file_size_bytes=1024000,
                variant_index=1,
            ),
        ]

        # Mock generation query
        gen_result = MagicMock()
        gen_result.scalar_one_or_none.return_value = sample_generation

        # Mock clips query
        clips_result = MagicMock()
        clips_result.scalars.return_value.all.return_value = clips

        veo_service.db.execute = AsyncMock(side_effect=[gen_result, clips_result])

        result = await veo_service.get_generation(generation_id)

        assert result is not None
        assert result.id == generation_id
        assert result.status == VeoGenerationStatus.COMPLETED
        assert len(result.clips) == 2
        assert result.clips[0].variant_index == 0
        assert result.clips[1].variant_index == 1

    async def test_regenerate_broll_uses_original_params(
        self,
        veo_service: VeoGeneratorService,
        sample_generation: GeneratedBRoll,
    ) -> None:
        """Test regenerate uses original generation parameters."""
        # Mock the original generation query
        gen_result = MagicMock()
        gen_result.scalar_one_or_none.return_value = sample_generation
        veo_service.db.execute = AsyncMock(return_value=gen_result)

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)

        veo_service.db.refresh = mock_refresh

        request = VeoRegenerateRequest(
            original_generation_id=sample_generation.id,
            # Only change the prompt
            prompt="Modified prompt for regeneration",
        )

        response = await veo_service.regenerate_broll(request)

        assert response.status == VeoGenerationStatus.PENDING
        assert response.prompt == "Modified prompt for regeneration"
        assert response.duration_seconds == sample_generation.duration_seconds
        assert response.style == VeoStyle(sample_generation.style)

    async def test_regenerate_broll_not_found(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test regenerate raises error for non-existent generation."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        veo_service.db.execute = AsyncMock(return_value=mock_result)

        request = VeoRegenerateRequest(
            original_generation_id=uuid.uuid4(),
        )

        with pytest.raises(ValueError, match="not found"):
            await veo_service.regenerate_broll(request)

    async def test_delete_generation(
        self,
        veo_service: VeoGeneratorService,
        sample_generation: GeneratedBRoll,
    ) -> None:
        """Test delete_generation removes generation and clips."""
        clips = [
            GeneratedBRollClip(
                id=uuid.uuid4(),
                generation_id=sample_generation.id,
                url="https://storage.example.com/clip1.mp4",
                duration_seconds=3.0,
                width=1080,
                height=1920,
                variant_index=0,
            )
        ]

        # Mock generation query
        gen_result = MagicMock()
        gen_result.scalar_one_or_none.return_value = sample_generation

        # Mock clips query
        clips_result = MagicMock()
        clips_result.scalars.return_value.all.return_value = clips

        veo_service.db.execute = AsyncMock(side_effect=[gen_result, clips_result])

        # Mock storage delete
        veo_service.storage.delete_file = MagicMock()

        result = await veo_service.delete_generation(sample_generation.id)

        assert result is True
        assert veo_service.db.delete.call_count >= 2  # Clip and generation
        assert veo_service.db.commit.call_count == 1

    async def test_delete_generation_not_found(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test delete returns False for non-existent generation."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        veo_service.db.execute = AsyncMock(return_value=mock_result)

        result = await veo_service.delete_generation(uuid.uuid4())

        assert result is False

    def test_build_enhanced_prompt_realistic(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test prompt enhancement for realistic style."""
        prompt = veo_service._build_enhanced_prompt(
            prompt="Person walking in a park",
            style=VeoStyle.REALISTIC,
            negative_prompt=None,
        )

        assert "Person walking in a park" in prompt
        assert "photorealistic" in prompt
        assert "high quality" in prompt

    def test_build_enhanced_prompt_cinematic(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test prompt enhancement for cinematic style."""
        prompt = veo_service._build_enhanced_prompt(
            prompt="Sunset over the ocean",
            style=VeoStyle.CINEMATIC,
            negative_prompt=None,
        )

        assert "Sunset over the ocean" in prompt
        assert "cinematic" in prompt
        assert "film-like" in prompt

    def test_build_enhanced_prompt_with_negative(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test prompt enhancement with negative prompt."""
        prompt = veo_service._build_enhanced_prompt(
            prompt="Product demonstration",
            style=VeoStyle.REALISTIC,
            negative_prompt="blurry, shaky",
        )

        assert "Product demonstration" in prompt
        assert "avoid" in prompt
        assert "blurry, shaky" in prompt

    def test_get_dimensions_vertical(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test dimensions for vertical aspect ratio."""
        width, height = veo_service._get_dimensions_for_aspect_ratio("9:16")
        assert width == 1080
        assert height == 1920

    def test_get_dimensions_horizontal(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test dimensions for horizontal aspect ratio."""
        width, height = veo_service._get_dimensions_for_aspect_ratio("16:9")
        assert width == 1920
        assert height == 1080

    def test_get_dimensions_square(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test dimensions for square aspect ratio."""
        width, height = veo_service._get_dimensions_for_aspect_ratio("1:1")
        assert width == 1080
        assert height == 1080

    @patch("app.services.veo_generator.genai")
    async def test_enhance_prompt(
        self,
        mock_genai: MagicMock,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test prompt enhancement using Gemini."""
        # Mock the Gemini response
        mock_response = MagicMock()
        mock_response.text = """```json
        {
            "enhanced_prompts": [
                "Enhanced prompt 1 with cinematic details",
                "Enhanced prompt 2 with professional lighting",
                "Enhanced prompt 3 with camera movement"
            ],
            "style_recommendations": ["cinematic", "realistic"]
        }
        ```"""

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        veo_service._client = mock_client

        request = PromptEnhancementRequest(
            original_prompt="Water splashing",
            context="For a product ad",
            style_hints=["professional", "clean"],
        )

        response = await veo_service.enhance_prompt(request)

        assert response.original_prompt == "Water splashing"
        assert len(response.enhanced_prompts) == 3
        assert VeoStyle.CINEMATIC in response.style_recommendations
        assert VeoStyle.REALISTIC in response.style_recommendations

    async def test_enhance_prompt_error_handling(
        self,
        veo_service: VeoGeneratorService,
    ) -> None:
        """Test enhance_prompt handles errors gracefully."""
        # Mock the client to raise an error
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        veo_service._client = mock_client

        request = PromptEnhancementRequest(
            original_prompt="Water splashing",
        )

        response = await veo_service.enhance_prompt(request)

        # Should return original prompt on error
        assert response.original_prompt == "Water splashing"
        assert response.enhanced_prompts == ["Water splashing"]


class TestVeoGenerateRequest:
    """Tests for VeoGenerateRequest validation."""

    def test_valid_request(self) -> None:
        """Test valid request creation."""
        request = VeoGenerateRequest(
            prompt="A beautiful sunset over mountains",
            duration_seconds=5.0,
            aspect_ratio=VeoAspectRatio.HORIZONTAL,
            style=VeoStyle.CINEMATIC,
            num_variants=3,
        )

        assert request.prompt == "A beautiful sunset over mountains"
        assert request.duration_seconds == 5.0
        assert request.aspect_ratio == VeoAspectRatio.HORIZONTAL
        assert request.style == VeoStyle.CINEMATIC
        assert request.num_variants == 3

    def test_prompt_too_short(self) -> None:
        """Test validation rejects too-short prompt."""
        with pytest.raises(ValueError):
            VeoGenerateRequest(
                prompt="short",  # Less than 10 chars
                duration_seconds=3.0,
            )

    def test_duration_too_short(self) -> None:
        """Test validation rejects duration under 1 second."""
        with pytest.raises(ValueError):
            VeoGenerateRequest(
                prompt="A valid prompt that is long enough",
                duration_seconds=0.5,
            )

    def test_duration_too_long(self) -> None:
        """Test validation rejects duration over 10 seconds."""
        with pytest.raises(ValueError):
            VeoGenerateRequest(
                prompt="A valid prompt that is long enough",
                duration_seconds=15.0,
            )

    def test_too_many_variants(self) -> None:
        """Test validation rejects more than 4 variants."""
        with pytest.raises(ValueError):
            VeoGenerateRequest(
                prompt="A valid prompt that is long enough",
                duration_seconds=3.0,
                num_variants=5,
            )

    def test_defaults(self) -> None:
        """Test default values are applied."""
        request = VeoGenerateRequest(
            prompt="A valid prompt that is long enough",
        )

        assert request.duration_seconds == 3.0
        assert request.aspect_ratio == VeoAspectRatio.VERTICAL
        assert request.style == VeoStyle.REALISTIC
        assert request.num_variants == 2
        assert request.project_id is None
        assert request.slot_id is None


class TestVeoRegenerateRequest:
    """Tests for VeoRegenerateRequest validation."""

    def test_minimal_request(self) -> None:
        """Test minimal regenerate request with only original ID."""
        original_id = uuid.uuid4()
        request = VeoRegenerateRequest(
            original_generation_id=original_id,
        )

        assert request.original_generation_id == original_id
        assert request.prompt is None
        assert request.duration_seconds is None
        assert request.style is None

    def test_with_overrides(self) -> None:
        """Test regenerate request with parameter overrides."""
        request = VeoRegenerateRequest(
            original_generation_id=uuid.uuid4(),
            prompt="New improved prompt for better results",
            style=VeoStyle.ANIMATED,
            num_variants=3,
        )

        assert request.prompt == "New improved prompt for better results"
        assert request.style == VeoStyle.ANIMATED
        assert request.num_variants == 3


class TestVeoAspectRatio:
    """Tests for VeoAspectRatio enum."""

    def test_vertical(self) -> None:
        """Test vertical aspect ratio value."""
        assert VeoAspectRatio.VERTICAL.value == "9:16"

    def test_horizontal(self) -> None:
        """Test horizontal aspect ratio value."""
        assert VeoAspectRatio.HORIZONTAL.value == "16:9"

    def test_square(self) -> None:
        """Test square aspect ratio value."""
        assert VeoAspectRatio.SQUARE.value == "1:1"


class TestVeoStyle:
    """Tests for VeoStyle enum."""

    def test_all_styles(self) -> None:
        """Test all style values exist."""
        assert VeoStyle.REALISTIC.value == "realistic"
        assert VeoStyle.CINEMATIC.value == "cinematic"
        assert VeoStyle.ANIMATED.value == "animated"
        assert VeoStyle.ARTISTIC.value == "artistic"
