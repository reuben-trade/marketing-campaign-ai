"""Tests for the recipe extraction service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad import Ad
from app.models.ad_element import AdElement
from app.models.recipe import Recipe
from app.schemas.recipe import BeatDefinition
from app.services.recipe_extractor import RecipeExtractionError, RecipeExtractor


class TestRecipeExtractor:
    """Tests for RecipeExtractor service."""

    @pytest.fixture
    def extractor(self) -> RecipeExtractor:
        """Create a RecipeExtractor instance."""
        return RecipeExtractor()

    @pytest.fixture
    def sample_video_intelligence(self) -> dict:
        """Create sample video_intelligence data."""
        return {
            "media_type": "video",
            "analysis_version": "2.0",
            "overall_pacing_score": 7,
            "production_style": "Authentic UGC",
            "hook_score": 8,
            "timeline": [
                {
                    "beat_type": "Hook",
                    "start_time": "00:00",
                    "end_time": "00:03",
                    "visual_description": "Fast-paced opening with bold text",
                    "cinematics": {
                        "camera_angle": "Close-up",
                        "lighting_style": "Natural",
                        "cinematic_features": ["fast_cuts", "text-overlay"],
                        "motion_type": "handheld",
                        "transition_out": "cut",
                    },
                    "rhetorical_appeal": {"mode": "Pathos"},
                    "text_overlays_in_beat": [{"text": "Stop scrolling!"}],
                    "emotion_intensity": 8,
                },
                {
                    "beat_type": "Problem",
                    "start_time": "00:03",
                    "end_time": "00:08",
                    "visual_description": "Showing the pain point",
                    "cinematics": {
                        "camera_angle": "Medium",
                        "lighting_style": "Natural",
                        "motion_type": "static",
                        "transition_out": "dissolve",
                    },
                    "rhetorical_appeal": {"mode": "Pathos"},
                    "emotion_intensity": 6,
                },
                {
                    "beat_type": "Solution",
                    "start_time": "00:08",
                    "end_time": "00:18",
                    "visual_description": "Product demonstration",
                    "cinematics": {
                        "camera_angle": "Close-up",
                        "lighting_style": "Studio",
                        "motion_type": "dolly",
                        "transition_out": "cut",
                    },
                    "rhetorical_appeal": {"mode": "Logos"},
                    "emotion_intensity": 5,
                },
                {
                    "beat_type": "CTA",
                    "start_time": "00:18",
                    "end_time": "00:22",
                    "visual_description": "Call to action with urgency",
                    "cinematics": {
                        "camera_angle": "Wide",
                        "lighting_style": "Bright",
                        "cinematic_features": ["text-overlay"],
                        "motion_type": "static",
                    },
                    "rhetorical_appeal": {"mode": "Kairos"},
                    "text_overlays_in_beat": [{"text": "Shop now!"}],
                    "emotion_intensity": 7,
                },
            ],
            "platform_optimization": {"duration_seconds": 22},
        }

    @pytest.fixture
    def sample_ad_with_video_intelligence(self, sample_video_intelligence: dict) -> Ad:
        """Create a sample Ad with video_intelligence."""
        ad = Ad(
            id=uuid.uuid4(),
            competitor_id=uuid.uuid4(),
            ad_library_id="test_ad_001",
            creative_type="video",
            creative_storage_path="test/path.mp4",
            analyzed=True,
            video_intelligence=sample_video_intelligence,
            composite_score=0.85,
        )
        return ad

    @pytest.fixture
    def sample_ad_elements(self) -> list[AdElement]:
        """Create sample AdElement objects."""
        ad_id = uuid.uuid4()
        return [
            AdElement(
                id=uuid.uuid4(),
                ad_id=ad_id,
                beat_index=0,
                beat_type="Hook",
                start_time="00:00",
                end_time="00:03",
                duration_seconds=3.0,
                visual_description="Attention-grabbing opener",
                camera_angle="Close-up",
                lighting_style="Natural",
                motion_type="handheld",
                cinematic_features=["fast_cuts"],
                rhetorical_mode="Pathos",
                transition_out="cut",
                emotion_intensity=8,
                text_overlays=[{"text": "Hey!"}],
            ),
            AdElement(
                id=uuid.uuid4(),
                ad_id=ad_id,
                beat_index=1,
                beat_type="Problem",
                start_time="00:03",
                end_time="00:08",
                duration_seconds=5.0,
                visual_description="Pain point demonstration",
                camera_angle="Medium",
                lighting_style="Natural",
                rhetorical_mode="Pathos",
                transition_out="dissolve",
                emotion_intensity=5,
            ),
            AdElement(
                id=uuid.uuid4(),
                ad_id=ad_id,
                beat_index=2,
                beat_type="CTA",
                start_time="00:08",
                end_time="00:12",
                duration_seconds=4.0,
                visual_description="Call to action",
                camera_angle="Wide",
                lighting_style="Bright",
                rhetorical_mode="Kairos",
                emotion_intensity=7,
                text_overlays=[{"text": "Buy Now!"}],
            ),
        ]

    @pytest.fixture
    def sample_ad_with_elements(self, sample_ad_elements: list[AdElement]) -> Ad:
        """Create a sample Ad with elements."""
        ad = Ad(
            id=sample_ad_elements[0].ad_id,
            competitor_id=uuid.uuid4(),
            ad_library_id="test_ad_002",
            creative_type="video",
            creative_storage_path="test/path2.mp4",
            analyzed=True,
            video_intelligence=None,
            composite_score=0.75,
        )
        ad.elements = sample_ad_elements
        return ad

    # =========================================================================
    # Timestamp Parsing Tests
    # =========================================================================

    def test_parse_timestamp_mm_ss(self, extractor: RecipeExtractor) -> None:
        """Test parsing MM:SS format."""
        assert extractor._parse_timestamp("01:30") == 90.0
        assert extractor._parse_timestamp("00:45") == 45.0
        assert extractor._parse_timestamp("02:00") == 120.0

    def test_parse_timestamp_hh_mm_ss(self, extractor: RecipeExtractor) -> None:
        """Test parsing HH:MM:SS format."""
        assert extractor._parse_timestamp("01:00:00") == 3600.0
        assert extractor._parse_timestamp("00:01:30") == 90.0

    def test_parse_timestamp_seconds_only(self, extractor: RecipeExtractor) -> None:
        """Test parsing seconds-only format."""
        assert extractor._parse_timestamp("45") == 45.0
        assert extractor._parse_timestamp("120.5") == 120.5

    def test_parse_timestamp_empty(self, extractor: RecipeExtractor) -> None:
        """Test parsing empty timestamp."""
        assert extractor._parse_timestamp("") == 0.0
        assert extractor._parse_timestamp(None) == 0.0  # type: ignore

    def test_parse_timestamp_invalid(self, extractor: RecipeExtractor) -> None:
        """Test parsing invalid timestamp."""
        assert extractor._parse_timestamp("invalid") == 0.0

    # =========================================================================
    # Duration Calculation Tests
    # =========================================================================

    def test_calculate_duration(self, extractor: RecipeExtractor) -> None:
        """Test duration calculation from timestamps."""
        assert extractor._calculate_duration("00:00", "00:30") == 30.0
        assert extractor._calculate_duration("01:00", "01:45") == 45.0
        assert extractor._calculate_duration("00:30", "00:00") == 0.0  # Negative returns 0

    # =========================================================================
    # Pacing Score Tests
    # =========================================================================

    def test_score_to_pacing(self, extractor: RecipeExtractor) -> None:
        """Test pacing score conversion."""
        assert extractor._score_to_pacing(1) == "slow"
        assert extractor._score_to_pacing(3) == "slow"
        assert extractor._score_to_pacing(4) == "medium"
        assert extractor._score_to_pacing(6) == "medium"
        assert extractor._score_to_pacing(7) == "fast"
        assert extractor._score_to_pacing(8) == "fast"
        assert extractor._score_to_pacing(9) == "dynamic"
        assert extractor._score_to_pacing(10) == "dynamic"
        assert extractor._score_to_pacing(None) == "medium"

    # =========================================================================
    # Characteristic Extraction Tests
    # =========================================================================

    def test_extract_characteristics_from_dict(self, extractor: RecipeExtractor) -> None:
        """Test extracting characteristics from dict beat."""
        beat = {
            "cinematics": {
                "cinematic_features": ["fast_cuts", "slow-mo"],
                "camera_angle": "Close-up",
                "motion_type": "handheld",
            },
            "text_overlays_in_beat": [{"text": "Test"}],
            "emotion_intensity": 8,
        }
        chars = extractor._extract_characteristics(beat)
        assert "fast_cuts" in chars
        assert "slow-mo" in chars
        assert "close-up" in chars
        assert "handheld" in chars
        assert "text_overlay" in chars
        assert "high_energy" in chars

    def test_extract_characteristics_from_ad_element(
        self, extractor: RecipeExtractor, sample_ad_elements: list[AdElement]
    ) -> None:
        """Test extracting characteristics from AdElement."""
        hook = sample_ad_elements[0]
        chars = extractor._extract_characteristics(hook)
        assert "fast_cuts" in chars
        assert "close-up" in chars
        assert "handheld" in chars
        assert "text_overlay" in chars
        assert "high_energy" in chars

    def test_extract_characteristics_low_energy(self, extractor: RecipeExtractor) -> None:
        """Test extracting calm characteristic from low intensity beat."""
        beat = {"emotion_intensity": 2}
        chars = extractor._extract_characteristics(beat)
        assert "calm" in chars

    # =========================================================================
    # Cinematics Extraction Tests
    # =========================================================================

    def test_extract_cinematics_from_dict(self, extractor: RecipeExtractor) -> None:
        """Test extracting cinematics from dict beat."""
        beat = {
            "cinematics": {
                "camera_angle": "Close-up",
                "lighting_style": "Natural",
                "color_grading": "warm",
                "motion_type": "handheld",
            }
        }
        cinematics = extractor._extract_cinematics(beat)
        assert cinematics is not None
        assert cinematics["camera_angle"] == "Close-up"
        assert cinematics["lighting_style"] == "Natural"
        assert cinematics["color_grading"] == "warm"
        assert cinematics["motion_type"] == "handheld"

    def test_extract_cinematics_empty(self, extractor: RecipeExtractor) -> None:
        """Test extracting cinematics from empty beat."""
        beat: dict = {"cinematics": {}}
        assert extractor._extract_cinematics(beat) is None

    # =========================================================================
    # Text Overlay Pattern Tests
    # =========================================================================

    def test_extract_text_overlay_pattern_hook(self, extractor: RecipeExtractor) -> None:
        """Test text overlay pattern for hook beat."""
        beat = {"beat_type": "Hook", "text_overlays_in_beat": [{"text": "Wow!"}]}
        assert extractor._extract_text_overlay_pattern(beat) == "attention_grabber"

    def test_extract_text_overlay_pattern_cta(self, extractor: RecipeExtractor) -> None:
        """Test text overlay pattern for CTA beat."""
        beat = {"beat_type": "CTA", "text_overlays_in_beat": [{"text": "Buy now!"}]}
        assert extractor._extract_text_overlay_pattern(beat) == "cta_text"

    def test_extract_text_overlay_pattern_benefit_stack(self, extractor: RecipeExtractor) -> None:
        """Test text overlay pattern for benefit stack beat."""
        beat = {"beat_type": "Benefit Stack", "text_overlays_in_beat": [{"text": "Fast"}]}
        assert extractor._extract_text_overlay_pattern(beat) == "benefit_list"

    def test_extract_text_overlay_pattern_no_overlays(self, extractor: RecipeExtractor) -> None:
        """Test text overlay pattern when no overlays present."""
        beat = {"beat_type": "Hook", "text_overlays_in_beat": []}
        assert extractor._extract_text_overlay_pattern(beat) is None

    # =========================================================================
    # Purpose Inference Tests
    # =========================================================================

    def test_infer_purpose(self, extractor: RecipeExtractor) -> None:
        """Test purpose inference from beat types."""
        assert "scroll" in extractor._infer_purpose("Hook").lower()
        assert "pain" in extractor._infer_purpose("Problem").lower()
        assert "answer" in extractor._infer_purpose("Solution").lower()
        assert "conversion" in extractor._infer_purpose("CTA").lower()

    # =========================================================================
    # Recipe Name Generation Tests
    # =========================================================================

    def test_generate_recipe_name_basic(self, extractor: RecipeExtractor) -> None:
        """Test basic recipe name generation."""
        structure = [
            BeatDefinition(beat_type="Hook", target_duration=3.0, purpose=""),
            BeatDefinition(beat_type="Problem", target_duration=5.0, purpose=""),
            BeatDefinition(beat_type="CTA", target_duration=4.0, purpose=""),
        ]
        name = extractor._generate_recipe_name(structure, None)
        assert "Hook" in name
        assert "PAS" in name  # Problem triggers PAS pattern
        assert "CTA" in name

    def test_generate_recipe_name_with_ugc_style(self, extractor: RecipeExtractor) -> None:
        """Test recipe name with UGC style."""
        structure = [
            BeatDefinition(beat_type="Hook", target_duration=3.0, purpose=""),
            BeatDefinition(beat_type="CTA", target_duration=4.0, purpose=""),
        ]
        name = extractor._generate_recipe_name(structure, "ugc")
        assert "UGC" in name

    def test_generate_recipe_name_with_polished_style(self, extractor: RecipeExtractor) -> None:
        """Test recipe name with polished style."""
        structure = [
            BeatDefinition(beat_type="Product Showcase", target_duration=10.0, purpose=""),
            BeatDefinition(beat_type="CTA", target_duration=4.0, purpose=""),
        ]
        name = extractor._generate_recipe_name(structure, "polished")
        assert "Polished" in name

    # =========================================================================
    # Style Mapping Tests
    # =========================================================================

    def test_style_mapping(self, extractor: RecipeExtractor) -> None:
        """Test production style to recipe style mapping."""
        assert extractor.STYLE_MAPPING["Authentic UGC"] == "ugc"
        assert extractor.STYLE_MAPPING["High-production Studio"] == "polished"
        assert extractor.STYLE_MAPPING["Talking Head"] == "talking_head"
        assert extractor.STYLE_MAPPING["Animation"] == "animation"
        assert extractor.STYLE_MAPPING["Unknown"] is None

    # =========================================================================
    # Full Extraction Tests (Integration)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_extract_from_ad_with_video_intelligence(
        self, extractor: RecipeExtractor, sample_ad_with_video_intelligence: Ad
    ) -> None:
        """Test extracting recipe from ad with video_intelligence."""
        # Create mock db session
        db = AsyncMock(spec=AsyncSession)

        # Mock the query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_ad_with_video_intelligence
        db.execute.return_value = mock_result

        # Mock add, commit, refresh
        captured_recipe = None

        def capture_add(recipe: Recipe) -> None:
            nonlocal captured_recipe
            captured_recipe = recipe

        db.add = MagicMock(side_effect=capture_add)
        db.commit = AsyncMock()

        async def mock_refresh(obj: Recipe) -> None:
            # Set created_at to simulate database behavior
            if captured_recipe and not captured_recipe.created_at:
                captured_recipe.created_at = datetime.now(timezone.utc)

        db.refresh = AsyncMock(side_effect=mock_refresh)

        result = await extractor.extract_from_ad(
            db, sample_ad_with_video_intelligence.id, custom_name=None
        )

        assert result is not None
        assert result.recipe is not None
        assert len(result.recipe.structure) == 4
        assert result.recipe.pacing == "fast"  # Score 7 -> fast
        assert result.recipe.style == "ugc"  # Authentic UGC -> ugc
        assert result.recipe.composite_score == 0.85
        assert "video_intelligence" in result.extraction_notes[0].lower()

        # Verify structure
        beat_types = [b.beat_type for b in result.recipe.structure]
        assert beat_types == ["Hook", "Problem", "Solution", "CTA"]

    @pytest.mark.asyncio
    async def test_extract_from_ad_with_elements(
        self, extractor: RecipeExtractor, sample_ad_with_elements: Ad
    ) -> None:
        """Test extracting recipe from ad with elements."""
        db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_ad_with_elements
        db.execute.return_value = mock_result

        captured_recipe = None

        def capture_add(recipe: Recipe) -> None:
            nonlocal captured_recipe
            captured_recipe = recipe

        db.add = MagicMock(side_effect=capture_add)
        db.commit = AsyncMock()

        async def mock_refresh(obj: Recipe) -> None:
            if captured_recipe and not captured_recipe.created_at:
                captured_recipe.created_at = datetime.now(timezone.utc)

        db.refresh = AsyncMock(side_effect=mock_refresh)

        result = await extractor.extract_from_ad(
            db, sample_ad_with_elements.id, custom_name="Custom Recipe Name"
        )

        assert result is not None
        assert result.recipe.name == "Custom Recipe Name"
        assert len(result.recipe.structure) == 3
        assert "ad_elements" in result.extraction_notes[0].lower()

    @pytest.mark.asyncio
    async def test_extract_from_ad_not_found(self, extractor: RecipeExtractor) -> None:
        """Test extracting recipe from non-existent ad."""
        db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(RecipeExtractionError) as exc_info:
            await extractor.extract_from_ad(db, uuid.uuid4())

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_extract_from_ad_not_analyzed(self, extractor: RecipeExtractor) -> None:
        """Test extracting recipe from unanalyzed ad."""
        db = AsyncMock(spec=AsyncSession)

        ad = Ad(
            id=uuid.uuid4(),
            competitor_id=uuid.uuid4(),
            ad_library_id="test_ad",
            creative_type="video",
            creative_storage_path="test/path.mp4",
            analyzed=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = ad
        db.execute.return_value = mock_result

        with pytest.raises(RecipeExtractionError) as exc_info:
            await extractor.extract_from_ad(db, ad.id)

        assert "not been analyzed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_extract_from_ad_no_timeline(self, extractor: RecipeExtractor) -> None:
        """Test extracting recipe from ad with no timeline data."""
        db = AsyncMock(spec=AsyncSession)

        ad = Ad(
            id=uuid.uuid4(),
            competitor_id=uuid.uuid4(),
            ad_library_id="test_ad",
            creative_type="video",
            creative_storage_path="test/path.mp4",
            analyzed=True,
            video_intelligence=None,
        )
        ad.elements = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = ad
        db.execute.return_value = mock_result

        with pytest.raises(RecipeExtractionError) as exc_info:
            await extractor.extract_from_ad(db, ad.id)

        assert "no timeline" in str(exc_info.value).lower()

    # =========================================================================
    # List/Get/Delete Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_recipe(self, extractor: RecipeExtractor) -> None:
        """Test getting a recipe by ID."""
        db = AsyncMock(spec=AsyncSession)

        recipe = Recipe(
            id=uuid.uuid4(),
            name="Test Recipe",
            structure=[{"beat_type": "Hook", "target_duration": 3.0}],
            created_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = recipe
        db.execute.return_value = mock_result

        result = await extractor.get_recipe(db, recipe.id)
        assert result == recipe

    @pytest.mark.asyncio
    async def test_get_recipe_not_found(self, extractor: RecipeExtractor) -> None:
        """Test getting a non-existent recipe."""
        db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await extractor.get_recipe(db, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_recipes(self, extractor: RecipeExtractor) -> None:
        """Test listing recipes."""
        db = AsyncMock(spec=AsyncSession)

        recipes = [
            Recipe(
                id=uuid.uuid4(),
                name="Recipe 1",
                structure=[{"beat_type": "Hook", "target_duration": 3.0}],
                composite_score=0.9,
                created_at=datetime.now(timezone.utc),
            ),
            Recipe(
                id=uuid.uuid4(),
                name="Recipe 2",
                structure=[{"beat_type": "CTA", "target_duration": 4.0}],
                composite_score=0.8,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # Mock recipes query
        mock_recipes_result = MagicMock()
        mock_recipes_result.scalars.return_value.all.return_value = recipes

        db.execute.side_effect = [mock_count_result, mock_recipes_result]

        result_recipes, total = await extractor.list_recipes(db)

        assert len(result_recipes) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_delete_recipe(self, extractor: RecipeExtractor) -> None:
        """Test deleting a recipe."""
        db = AsyncMock(spec=AsyncSession)

        recipe = Recipe(
            id=uuid.uuid4(),
            name="Test Recipe",
            structure=[{"beat_type": "Hook", "target_duration": 3.0}],
            created_at=datetime.now(timezone.utc),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = recipe
        db.execute.return_value = mock_result

        db.delete = AsyncMock()
        db.commit = AsyncMock()

        result = await extractor.delete_recipe(db, recipe.id)
        assert result is True
        db.delete.assert_called_once_with(recipe)
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_recipe_not_found(self, extractor: RecipeExtractor) -> None:
        """Test deleting a non-existent recipe."""
        db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await extractor.delete_recipe(db, uuid.uuid4())
        assert result is False

    # =========================================================================
    # Target Duration Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_target_duration_from_source(
        self, extractor: RecipeExtractor, sample_ad_with_video_intelligence: Ad
    ) -> None:
        """Test that target duration captures source ad timing as a guideline."""
        db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_ad_with_video_intelligence
        db.execute.return_value = mock_result

        captured_recipe = None

        def capture_add(recipe: Recipe) -> None:
            nonlocal captured_recipe
            captured_recipe = recipe

        db.add = MagicMock(side_effect=capture_add)
        db.commit = AsyncMock()

        async def mock_refresh(obj: Recipe) -> None:
            if captured_recipe and not captured_recipe.created_at:
                captured_recipe.created_at = datetime.now(timezone.utc)

        db.refresh = AsyncMock(side_effect=mock_refresh)

        result = await extractor.extract_from_ad(db, sample_ad_with_video_intelligence.id)

        # Hook is 3 seconds (00:00 to 00:03) - stored as guideline, not enforced
        hook_beat = result.recipe.structure[0]
        assert hook_beat.target_duration == 3.0

        # Problem is 5 seconds (00:03 to 00:08)
        problem_beat = result.recipe.structure[1]
        assert problem_beat.target_duration == 5.0
