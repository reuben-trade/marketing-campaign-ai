"""Tests for Director Validator - JSON extraction, validation, and repair."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.director_output import (
    DirectorLLMOutput,
    DirectorVideoSettings,
    VideoClipEntry,
)
from app.services.director_validator import DirectorValidator, ValidationResult


@pytest.fixture
def mock_genai():
    """Create a mock google.generativeai module."""
    mock_module = MagicMock()
    mock_types = MagicMock()
    mock_module.types = mock_types

    # Store original modules if they exist
    original_google = sys.modules.get("google")
    original_genai = sys.modules.get("google.generativeai")

    # Install mock
    sys.modules["google.generativeai"] = mock_module

    yield mock_module

    # Restore original modules
    if original_genai is not None:
        sys.modules["google.generativeai"] = original_genai
    elif "google.generativeai" in sys.modules:
        del sys.modules["google.generativeai"]
    if original_google is not None:
        sys.modules["google"] = original_google


class TestJSONExtraction:
    """Tests for JSON extraction from LLM responses."""

    @pytest.fixture
    def validator(self):
        return DirectorValidator()

    def test_extract_json_from_code_block(self, validator):
        """Extract JSON from markdown code block."""
        response = """Here's the video script:

```json
{
    "video_settings": {"target_duration_seconds": 30},
    "timeline": [
        {
            "entry_type": "video_clip",
            "start_seconds": 0,
            "duration_seconds": 5,
            "purpose": "Hook",
            "segment_id": "abc-123",
            "source_start_seconds": 0,
            "source_end_seconds": 5
        }
    ]
}
```

Let me know if you need changes!"""

        json_str = validator._extract_json(response)
        assert json_str is not None
        data = json.loads(json_str)
        assert data["video_settings"]["target_duration_seconds"] == 30

    def test_extract_json_from_unmarked_code_block(self, validator):
        """Extract JSON from code block without json marker."""
        response = """
```
{
    "video_settings": {"target_duration_seconds": 30},
    "timeline": []
}
```
"""
        json_str = validator._extract_json(response)
        assert json_str is not None

    def test_extract_raw_json(self, validator):
        """Extract JSON when no code block present."""
        response = """{
    "video_settings": {"target_duration_seconds": 30},
    "timeline": [
        {
            "entry_type": "video_clip",
            "start_seconds": 0,
            "duration_seconds": 5,
            "purpose": "Hook",
            "segment_id": "abc-123",
            "source_start_seconds": 0,
            "source_end_seconds": 5
        }
    ]
}"""
        json_str = validator._extract_json(response)
        assert json_str is not None
        data = json.loads(json_str)
        assert "video_settings" in data

    def test_extract_json_with_leading_text(self, validator):
        """Extract JSON with text before it."""
        response = """Based on my analysis, here is the video script:
{
    "video_settings": {"target_duration_seconds": 30},
    "timeline": []
}"""
        json_str = validator._extract_json(response)
        assert json_str is not None

    def test_extract_json_with_trailing_text(self, validator):
        """Extract JSON with text after it."""
        response = """{
    "video_settings": {"target_duration_seconds": 30},
    "timeline": []
}

This should create an engaging video."""
        json_str = validator._extract_json(response)
        assert json_str is not None

    def test_extract_json_empty_response(self, validator):
        """Handle empty response."""
        assert validator._extract_json("") is None
        assert validator._extract_json("   ") is None
        assert validator._extract_json(None) is None

    def test_extract_json_no_json(self, validator):
        """Handle response with no JSON."""
        response = "I cannot generate a video script without more information."
        assert validator._extract_json(response) is None

    def test_extract_json_invalid_json(self, validator):
        """Handle response with invalid JSON syntax."""
        response = """{
    "video_settings": {"target_duration_seconds": 30,}
    "timeline": []
}"""  # Note: trailing comma and missing comma
        # Should return None since it's not valid JSON
        json_str = validator._extract_json(response)
        # The regex will find it, but _is_valid_json will reject it
        assert json_str is None


class TestValidation:
    """Tests for Pydantic schema validation."""

    @pytest.fixture
    def validator(self):
        return DirectorValidator()

    @pytest.fixture
    def valid_response(self):
        """A valid Director LLM response."""
        return json.dumps(
            {
                "video_settings": {
                    "target_duration_seconds": 30,
                    "aspect_ratio": "9:16",
                },
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook - high attention",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                    {
                        "entry_type": "title_card",
                        "start_seconds": 5,
                        "duration_seconds": 3,
                        "purpose": "Brand intro",
                        "headline": "SUMMER SALE",
                    },
                ],
            }
        )

    def test_validate_valid_response(self, validator, valid_response):
        """Validate a correct response."""
        result = validator.validate(valid_response, auto_repair=False)

        assert result.success is True
        assert result.output is not None
        assert len(result.output.timeline) == 2
        assert result.errors == []

    def test_validate_with_code_block(self, validator):
        """Validate response wrapped in code block."""
        response = """```json
{
    "video_settings": {"target_duration_seconds": 30},
    "timeline": [
        {
            "entry_type": "video_clip",
            "start_seconds": 0,
            "duration_seconds": 5,
            "purpose": "Hook",
            "segment_id": "clip-001",
            "source_start_seconds": 0,
            "source_end_seconds": 5
        }
    ]
}
```"""
        result = validator.validate(response, auto_repair=False)
        assert result.success is True

    def test_validate_missing_required_field(self, validator):
        """Detect missing required field."""
        response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        # Missing: purpose, segment_id, source_start_seconds, source_end_seconds
                    },
                ],
            }
        )

        result = validator.validate(response, auto_repair=False)
        assert result.success is False
        assert len(result.errors) > 0
        assert any("purpose" in e or "segment_id" in e for e in result.errors)

    def test_validate_invalid_enum_value(self, validator):
        """Detect invalid enum value."""
        response = json.dumps(
            {
                "video_settings": {
                    "target_duration_seconds": 30,
                    "aspect_ratio": "invalid_ratio",  # Invalid enum
                },
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        result = validator.validate(response, auto_repair=False)
        assert result.success is False
        assert any("aspect_ratio" in e for e in result.errors)

    def test_validate_timeline_not_starting_at_zero(self, validator):
        """Detect timeline not starting at 0."""
        response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 5,  # Should be 0
                        "duration_seconds": 5,
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        result = validator.validate(response, auto_repair=False)
        assert result.success is False
        assert any("start at 0" in e for e in result.errors)

    def test_validate_duration_out_of_range(self, validator):
        """Detect duration outside allowed range."""
        response = json.dumps(
            {
                "video_settings": {
                    "target_duration_seconds": 10,  # Too short (min 15)
                },
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        result = validator.validate(response, auto_repair=False)
        assert result.success is False
        assert any("15" in e or "greater" in e.lower() for e in result.errors)

    def test_validate_segment_duration_too_long(self, validator):
        """Detect segment duration over 10s limit."""
        response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 15,  # Too long (max 10)
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 15,
                    },
                ],
            }
        )

        result = validator.validate(response, auto_repair=False)
        assert result.success is False
        assert any("10" in e or "less" in e.lower() for e in result.errors)


class TestSemanticValidation:
    """Tests for semantic validations (warnings, not errors)."""

    @pytest.fixture
    def validator(self):
        return DirectorValidator()

    def test_warn_timeline_gap(self, validator):
        """Warn about gaps in timeline."""
        response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 10,  # Gap: should be 5
                        "duration_seconds": 5,
                        "purpose": "Content",
                        "segment_id": "clip-002",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        result = validator.validate(response, auto_repair=False)
        assert result.success is True  # Gaps are warnings, not errors
        assert any("gap" in w.lower() for w in result.warnings)

    def test_warn_timeline_overlap(self, validator):
        """Warn about overlapping segments."""
        response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 3,  # Overlap: should be 5
                        "duration_seconds": 5,
                        "purpose": "Content",
                        "segment_id": "clip-002",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        result = validator.validate(response, auto_repair=False)
        assert result.success is True
        assert any("overlap" in w.lower() for w in result.warnings)

    def test_warn_duration_mismatch(self, validator):
        """Warn when actual duration differs significantly from target."""
        response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,  # Only 5s, target is 30s
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        result = validator.validate(response, auto_repair=False)
        assert result.success is True
        assert any("duration" in w.lower() and "mismatch" in w.lower() for w in result.warnings)

    def test_warn_invalid_clip_id(self, validator):
        """Warn when clip ID doesn't exist in provided list."""
        response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook",
                        "segment_id": "nonexistent-clip",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        valid_clip_ids = ["clip-001", "clip-002", "clip-003"]
        result = validator.validate(response, auto_repair=False, clip_ids=valid_clip_ids)

        assert result.success is True
        assert any("nonexistent-clip" in w and "not found" in w for w in result.warnings)

    def test_no_warn_valid_clip_id(self, validator):
        """No warning when clip ID exists in provided list."""
        response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        valid_clip_ids = ["clip-001", "clip-002", "clip-003"]
        result = validator.validate(response, auto_repair=False, clip_ids=valid_clip_ids)

        assert result.success is True
        assert not any("clip-001" in w and "not found" in w for w in result.warnings)


class TestAutoRepair:
    """Tests for auto-repair functionality."""

    @pytest.fixture
    def validator(self):
        return DirectorValidator()

    def test_repair_invalid_json(self, validator, mock_genai):
        """Test repair of invalid JSON syntax."""
        # Mock Gemini response with fixed JSON
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Invalid JSON input
        invalid_response = """{
            "video_settings": {"target_duration_seconds": 30,},
            "timeline": []
        }"""

        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(google_api_key="test-key")
            result = validator.validate(invalid_response, auto_repair=True)

        assert result.repair_attempted is True
        assert result.repair_succeeded is True
        assert result.success is True
        assert result.output is not None

    def test_repair_missing_field(self, validator, mock_genai):
        """Test repair of missing required field."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook - added by repair",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Missing "purpose" field
        invalid_response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(google_api_key="test-key")
            result = validator.validate(invalid_response, auto_repair=True)

        assert result.repair_attempted is True
        assert result.repair_succeeded is True
        assert result.success is True

    def test_no_repair_when_disabled(self, validator):
        """Test that repair is not attempted when auto_repair=False."""
        invalid_response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [],  # Empty timeline not allowed
            }
        )

        result = validator.validate(invalid_response, auto_repair=False)

        assert result.success is False
        assert result.repair_attempted is False


class TestExtractAndValidate:
    """Tests for the convenience method."""

    @pytest.fixture
    def validator(self):
        return DirectorValidator()

    def test_extract_and_validate_success(self, validator):
        """Test successful extraction and validation."""
        response = json.dumps(
            {
                "video_settings": {"target_duration_seconds": 30},
                "timeline": [
                    {
                        "entry_type": "video_clip",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "purpose": "Hook",
                        "segment_id": "clip-001",
                        "source_start_seconds": 0,
                        "source_end_seconds": 5,
                    },
                ],
            }
        )

        output = validator.extract_and_validate(response, auto_repair=False)

        assert isinstance(output, DirectorLLMOutput)
        assert len(output.timeline) == 1

    def test_extract_and_validate_raises_on_failure(self, validator):
        """Test that ValueError is raised on failure."""
        invalid_response = "This is not JSON at all"

        with pytest.raises(ValueError) as exc_info:
            validator.extract_and_validate(invalid_response, auto_repair=False)

        assert "validation failed" in str(exc_info.value).lower()


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_default_values(self):
        """Test default values are correct."""
        result = ValidationResult(success=False)

        assert result.success is False
        assert result.output is None
        assert result.raw_json is None
        assert result.errors == []
        assert result.warnings == []
        assert result.repair_attempted is False
        assert result.repair_succeeded is False

    def test_with_values(self):
        """Test with explicit values."""
        output = DirectorLLMOutput(
            video_settings=DirectorVideoSettings(target_duration_seconds=30),
            timeline=[
                VideoClipEntry(
                    start_seconds=0,
                    duration_seconds=5,
                    purpose="Test",
                    segment_id="test-id",
                    source_start_seconds=0,
                    source_end_seconds=5,
                ),
            ],
        )

        result = ValidationResult(
            success=True,
            output=output,
            raw_json={"video_settings": {}},
            errors=["error1"],
            warnings=["warning1"],
            repair_attempted=True,
            repair_succeeded=True,
        )

        assert result.success is True
        assert result.output is output
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
