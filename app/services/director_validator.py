"""Director Validator - extracts, validates, and repairs Director LLM output.

This service handles the messy reality of LLM output:
1. Extract JSON from raw LLM text (handles markdown code blocks, etc.)
2. Validate against DirectorLLMOutput Pydantic schema
3. Auto-repair common issues using Gemini Flash if validation fails
"""

import json
import logging
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.schemas.director_output import DirectorLLMOutput

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating Director output."""

    success: bool
    output: DirectorLLMOutput | None = None
    raw_json: dict | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    repair_attempted: bool = False
    repair_succeeded: bool = False


class DirectorValidator:
    """Validates and repairs Director LLM output.

    Usage:
        validator = DirectorValidator()
        result = validator.validate(llm_response_text)

        if result.success:
            payload = result.output
        else:
            print(result.errors)
    """

    # Regex patterns for JSON extraction
    JSON_CODE_BLOCK_PATTERN = re.compile(
        r"```(?:json)?\s*\n?([\s\S]*?)\n?```",
        re.IGNORECASE,
    )
    JSON_OBJECT_PATTERN = re.compile(
        r"\{[\s\S]*\}",
        re.MULTILINE,
    )

    def __init__(self, repair_model: str = "gemini-2.0-flash"):
        """Initialize validator.

        Args:
            repair_model: Gemini model to use for JSON repair
        """
        self.repair_model = repair_model
        self._gemini_client = None

    def validate(
        self,
        llm_response: str,
        auto_repair: bool = True,
        clip_ids: list[str] | None = None,
    ) -> ValidationResult:
        """Validate Director LLM output.

        Args:
            llm_response: Raw text response from the LLM
            auto_repair: Whether to attempt auto-repair on failure
            clip_ids: Valid clip IDs for reference validation

        Returns:
            ValidationResult with success status and parsed output or errors
        """
        result = ValidationResult(success=False)

        # Step 1: Extract JSON from response
        json_str = self._extract_json(llm_response)
        if not json_str:
            result.errors.append("No valid JSON found in LLM response")
            if auto_repair:
                return self._attempt_repair(llm_response, result, clip_ids)
            return result

        # Step 2: Parse JSON
        try:
            raw_json = json.loads(json_str)
            result.raw_json = raw_json
        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {e}")
            if auto_repair:
                return self._attempt_repair(llm_response, result, clip_ids)
            return result

        # Step 3: Validate against Pydantic schema
        try:
            result.output = DirectorLLMOutput.model_validate(raw_json)
            result.success = True
        except ValidationError as e:
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                result.errors.append(f"{loc}: {error['msg']}")

            if auto_repair:
                return self._attempt_repair(
                    llm_response, result, clip_ids, validation_errors=e.errors()
                )
            return result

        # Step 4: Additional semantic validations
        self._validate_semantics(result, clip_ids)

        return result

    def _extract_json(self, text: str) -> str | None:
        """Extract JSON from LLM response text.

        Handles:
        - JSON wrapped in ```json ... ``` code blocks
        - JSON wrapped in ``` ... ``` code blocks
        - Raw JSON object in response
        - JSON with leading/trailing text

        Args:
            text: Raw LLM response

        Returns:
            Extracted JSON string or None if not found
        """
        if not text or not text.strip():
            return None

        text = text.strip()

        # Try 1: Look for JSON in code blocks
        code_block_match = self.JSON_CODE_BLOCK_PATTERN.search(text)
        if code_block_match:
            json_str = code_block_match.group(1).strip()
            if self._is_valid_json(json_str):
                return json_str

        # Try 2: Look for raw JSON object
        # Find the first { and last } to extract potential JSON
        json_match = self.JSON_OBJECT_PATTERN.search(text)
        if json_match:
            json_str = json_match.group(0)
            if self._is_valid_json(json_str):
                return json_str

        # Try 3: Maybe the whole response is JSON
        if self._is_valid_json(text):
            return text

        return None

    def _is_valid_json(self, text: str) -> bool:
        """Check if text is valid JSON."""
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, TypeError):
            return False

    def _validate_semantics(
        self,
        result: ValidationResult,
        clip_ids: list[str] | None,
    ) -> None:
        """Perform additional semantic validations.

        These are warnings, not errors - the output is still usable.
        """
        if not result.output:
            return

        # Check timeline continuity
        timeline = result.output.timeline
        for i in range(1, len(timeline)):
            prev_end = timeline[i - 1].start_seconds + timeline[i - 1].duration_seconds
            curr_start = timeline[i].start_seconds
            gap = curr_start - prev_end

            if gap > 0.1:
                result.warnings.append(
                    f"Timeline gap of {gap:.2f}s between segments {i - 1} and {i}"
                )
            elif gap < -0.1:
                result.warnings.append(
                    f"Timeline overlap of {abs(gap):.2f}s between segments {i - 1} and {i}"
                )

        # Check total duration vs target
        actual_duration = result.output.get_total_duration()
        target_duration = result.output.video_settings.target_duration_seconds
        duration_diff = abs(actual_duration - target_duration)

        if duration_diff > 5:
            result.warnings.append(
                f"Duration mismatch: target {target_duration}s, actual {actual_duration:.1f}s"
            )

        # Validate clip IDs if provided
        if clip_ids:
            self._validate_clip_references(result, clip_ids)

    def _validate_clip_references(
        self,
        result: ValidationResult,
        valid_clip_ids: list[str],
    ) -> None:
        """Check that all referenced clip IDs exist."""
        if not result.output:
            return

        valid_ids_set = set(valid_clip_ids)

        for i, entry in enumerate(result.output.timeline):
            entry_type = entry.entry_type.value

            # Check segment_id for video clips
            if hasattr(entry, "segment_id"):
                if entry.segment_id not in valid_ids_set:
                    result.warnings.append(
                        f"Timeline[{i}] ({entry_type}): segment_id '{entry.segment_id}' not found"
                    )

            # Check main_segment_id and overlay_segment_id for B-roll overlays
            if hasattr(entry, "main_segment_id"):
                if entry.main_segment_id not in valid_ids_set:
                    result.warnings.append(
                        f"Timeline[{i}] ({entry_type}): main_segment_id '{entry.main_segment_id}' not found"
                    )

            if hasattr(entry, "overlay_segment_id"):
                if entry.overlay_segment_id not in valid_ids_set:
                    result.warnings.append(
                        f"Timeline[{i}] ({entry_type}): overlay_segment_id '{entry.overlay_segment_id}' not found"
                    )

    def _attempt_repair(
        self,
        original_response: str,
        result: ValidationResult,
        clip_ids: list[str] | None,
        validation_errors: list[dict] | None = None,
    ) -> ValidationResult:
        """Attempt to repair invalid JSON using Gemini Flash.

        Args:
            original_response: The original LLM response
            result: Current validation result with errors
            clip_ids: Valid clip IDs for context
            validation_errors: Pydantic validation errors if any

        Returns:
            Updated ValidationResult
        """
        result.repair_attempted = True

        try:
            repaired_json = self._repair_with_gemini(
                original_response,
                result.errors,
                validation_errors,
            )

            if not repaired_json:
                result.errors.append("Repair failed: Gemini returned no valid JSON")
                return result

            # Try to validate the repaired JSON
            try:
                result.output = DirectorLLMOutput.model_validate(repaired_json)
                result.raw_json = repaired_json
                result.success = True
                result.repair_succeeded = True
                result.warnings.append("Output was repaired by Gemini Flash")

                # Run semantic validations on repaired output
                self._validate_semantics(result, clip_ids)

            except ValidationError as e:
                for error in e.errors():
                    loc = " -> ".join(str(x) for x in error["loc"])
                    result.errors.append(f"Post-repair validation: {loc}: {error['msg']}")

        except Exception as e:
            result.errors.append(f"Repair failed with exception: {e}")
            logger.exception("Error during JSON repair")

        return result

    def _repair_with_gemini(
        self,
        original_response: str,
        errors: list[str],
        validation_errors: list[dict] | None,
    ) -> dict | None:
        """Use Gemini Flash to repair malformed JSON.

        Args:
            original_response: The original LLM response
            errors: List of error messages
            validation_errors: Pydantic validation errors

        Returns:
            Repaired JSON dict or None
        """
        try:
            import google.generativeai as genai

            from app.config import get_settings

            settings = get_settings()
            genai.configure(api_key=settings.google_api_key)

            model = genai.GenerativeModel(self.repair_model)
        except ImportError:
            logger.error("google-generativeai not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            return None

        # Build error context for the repair prompt
        error_context = "\n".join(f"- {e}" for e in errors)
        if validation_errors:
            validation_context = "\n".join(
                f"- {err['loc']}: {err['msg']}" for err in validation_errors[:10]
            )
            error_context += f"\n\nValidation errors:\n{validation_context}"

        # Get the schema for reference
        schema_json = json.dumps(
            DirectorLLMOutput.model_json_schema(),
            indent=2,
        )

        repair_prompt = f"""Fix the following JSON to match the required schema.

ERRORS FOUND:
{error_context}

REQUIRED SCHEMA:
{schema_json}

ORIGINAL RESPONSE:
{original_response}

INSTRUCTIONS:
1. Extract or reconstruct valid JSON matching the schema
2. Fix any syntax errors (missing quotes, commas, brackets)
3. Ensure all required fields are present with valid values
4. Ensure timeline starts at 0 seconds
5. Ensure all enum values are valid
6. Output ONLY the fixed JSON, no explanation

FIXED JSON:"""

        try:
            response = model.generate_content(
                repair_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for deterministic repair
                    max_output_tokens=8192,
                ),
            )

            repaired_text = response.text.strip()

            # Extract JSON from repair response
            repaired_json_str = self._extract_json(repaired_text)
            if repaired_json_str:
                return json.loads(repaired_json_str)

            # Try parsing the whole response as JSON
            return json.loads(repaired_text)

        except Exception as e:
            logger.error(f"Gemini repair failed: {e}")
            return None

    def extract_and_validate(
        self,
        llm_response: str,
        auto_repair: bool = True,
        clip_ids: list[str] | None = None,
    ) -> DirectorLLMOutput:
        """Extract, validate, and return DirectorLLMOutput or raise.

        Convenience method that raises on failure instead of returning result.

        Args:
            llm_response: Raw LLM response text
            auto_repair: Whether to attempt auto-repair
            clip_ids: Valid clip IDs for validation

        Returns:
            Validated DirectorLLMOutput

        Raises:
            ValueError: If validation fails
        """
        result = self.validate(llm_response, auto_repair, clip_ids)

        if not result.success:
            error_msg = "; ".join(result.errors)
            raise ValueError(f"Director output validation failed: {error_msg}")

        return result.output
