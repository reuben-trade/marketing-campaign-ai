"""Service for generating B-Roll video clips using Google's Veo 2 API."""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.generated_broll import GeneratedBRoll, GeneratedBRollClip
from app.schemas.veo_request import (
    PromptEnhancementRequest,
    PromptEnhancementResponse,
    VeoAspectRatio,
    VeoGeneratedClip,
    VeoGenerateRequest,
    VeoGenerationResponse,
    VeoGenerationStatus,
    VeoRegenerateRequest,
    VeoStyle,
)
from app.utils.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)


# Map our styles to prompt modifiers
STYLE_PROMPT_MODIFIERS = {
    VeoStyle.REALISTIC: "photorealistic, real-world footage style",
    VeoStyle.CINEMATIC: "cinematic, professional cinematography, film-like quality",
    VeoStyle.ANIMATED: "animated, smooth animation style",
    VeoStyle.ARTISTIC: "artistic, creative visual style",
}

# Output bucket for generated B-Roll clips
BROLL_OUTPUT_BUCKET = "generated-broll"


class VeoGeneratorService:
    """Service for generating B-Roll clips using Veo 2."""

    def __init__(self, db: AsyncSession):
        """Initialize the Veo generator service."""
        self.db = db
        self.storage = SupabaseStorage()
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        """Get or create the Gemini client."""
        if self._client is None:
            settings = get_settings()
            self._client = genai.Client(api_key=settings.google_api_key)
        return self._client

    async def generate_broll(
        self,
        request: VeoGenerateRequest,
    ) -> VeoGenerationResponse:
        """
        Generate B-Roll video clips using Veo 2.

        Creates a generation job and starts the video generation process.
        The actual generation happens asynchronously.
        """
        settings = get_settings()

        # Validate Veo is enabled
        if not settings.veo_enabled:
            raise ValueError("Veo 2 B-Roll generation is disabled")

        # Enforce config limits
        if request.num_variants > settings.veo_max_variants:
            raise ValueError(
                f"Number of variants ({request.num_variants}) exceeds maximum "
                f"allowed ({settings.veo_max_variants})"
            )

        if request.duration_seconds > settings.veo_max_duration_seconds:
            raise ValueError(
                f"Duration ({request.duration_seconds}s) exceeds maximum "
                f"allowed ({settings.veo_max_duration_seconds}s)"
            )

        # Create the generation record
        generation = GeneratedBRoll(
            prompt=request.prompt,
            duration_seconds=request.duration_seconds,
            aspect_ratio=request.aspect_ratio.value,
            style=request.style.value,
            num_variants=request.num_variants,
            project_id=request.project_id,
            slot_id=request.slot_id,
            negative_prompt=request.negative_prompt,
            seed=request.seed,
            status=VeoGenerationStatus.PENDING.value,
        )
        self.db.add(generation)
        await self.db.commit()
        await self.db.refresh(generation)

        logger.info(f"Created B-Roll generation job {generation.id}")

        return VeoGenerationResponse(
            id=generation.id,
            status=VeoGenerationStatus.PENDING,
            prompt=generation.prompt,
            duration_seconds=generation.duration_seconds,
            aspect_ratio=VeoAspectRatio(generation.aspect_ratio),
            style=VeoStyle(generation.style),
            num_variants=generation.num_variants,
            clips=[],
            project_id=generation.project_id,
            slot_id=generation.slot_id,
            created_at=generation.created_at,
        )

    async def start_generation(self, generation_id: uuid.UUID) -> VeoGenerationResponse:
        """
        Start the actual video generation process.

        This should be called in a background task after create_generation.
        """
        generation = await self._get_generation(generation_id)
        if not generation:
            raise ValueError(f"Generation {generation_id} not found")

        if generation.status != VeoGenerationStatus.PENDING.value:
            raise ValueError(f"Cannot start generation in status: {generation.status}")

        # Update status to processing
        generation.status = VeoGenerationStatus.PROCESSING.value
        await self.db.commit()

        start_time = time.time()

        try:
            # Build the enhanced prompt
            enhanced_prompt = self._build_enhanced_prompt(
                prompt=generation.prompt,
                style=VeoStyle(generation.style),
                negative_prompt=generation.negative_prompt,
            )

            # Generate videos using Veo 2
            clips = await self._generate_videos(
                prompt=enhanced_prompt,
                duration_seconds=generation.duration_seconds,
                aspect_ratio=generation.aspect_ratio,
                num_variants=generation.num_variants,
                generation_id=generation.id,
                project_id=generation.project_id,
            )

            # Update generation with results
            generation.status = VeoGenerationStatus.COMPLETED.value
            generation.completed_at = datetime.now(timezone.utc)
            generation.generation_time_seconds = time.time() - start_time

            # Save clips to database
            for i, clip_data in enumerate(clips):
                clip = GeneratedBRollClip(
                    generation_id=generation.id,
                    url=clip_data["url"],
                    thumbnail_url=clip_data.get("thumbnail_url"),
                    duration_seconds=clip_data["duration_seconds"],
                    width=clip_data["width"],
                    height=clip_data["height"],
                    file_size_bytes=clip_data.get("file_size_bytes"),
                    variant_index=i,
                )
                self.db.add(clip)

            await self.db.commit()
            await self.db.refresh(generation)

            logger.info(
                f"Generation {generation_id} completed with {len(clips)} clips "
                f"in {generation.generation_time_seconds:.1f}s"
            )

        except Exception as e:
            generation.status = VeoGenerationStatus.FAILED.value
            generation.error_message = str(e)
            generation.completed_at = datetime.now(timezone.utc)
            generation.generation_time_seconds = time.time() - start_time
            await self.db.commit()

            logger.error(f"Generation {generation_id} failed: {e}")
            raise

        return await self.get_generation(generation_id)

    async def _generate_videos(
        self,
        prompt: str,
        duration_seconds: float,
        aspect_ratio: str,
        num_variants: int,
        generation_id: uuid.UUID,
        project_id: uuid.UUID | None,
    ) -> list[dict]:
        """
        Generate videos using the Veo 2 API.

        Returns a list of clip dictionaries with url, dimensions, etc.
        """
        clips = []

        # Calculate dimensions based on aspect ratio
        width, height = self._get_dimensions_for_aspect_ratio(aspect_ratio)

        # Generate each variant
        for variant_idx in range(num_variants):
            logger.info(
                f"Generating variant {variant_idx + 1}/{num_variants} for generation {generation_id}"
            )

            try:
                # Use Veo 2 via Gemini API
                settings = get_settings()
                operation = await asyncio.to_thread(
                    self.client.models.generate_videos,
                    model=settings.veo_model,
                    prompt=prompt,
                    config=types.GenerateVideosConfig(
                        aspect_ratio=aspect_ratio,
                        number_of_videos=1,
                        duration_seconds=int(duration_seconds),
                        person_generation="allow_adult",
                    ),
                )

                # Poll for completion
                video_result = await self._poll_video_operation(operation)

                if video_result and video_result.generated_videos:
                    for video in video_result.generated_videos:
                        if video.video and video.video.video_bytes:
                            # Upload video to storage
                            storage_path = f"generations/{generation_id}/{variant_idx}.mp4"
                            url = await self._upload_video_to_storage(
                                video_data=video.video.video_bytes,
                                storage_path=storage_path,
                            )

                            clips.append(
                                {
                                    "url": url,
                                    "thumbnail_url": None,  # Could extract first frame
                                    "duration_seconds": duration_seconds,
                                    "width": width,
                                    "height": height,
                                    "file_size_bytes": len(video.video.video_bytes),
                                }
                            )

            except Exception as e:
                logger.warning(f"Failed to generate variant {variant_idx}: {e}")
                # Continue with other variants even if one fails
                if variant_idx == 0 and num_variants == 1:
                    # If first variant fails and it's the only one, re-raise
                    raise

        if not clips:
            raise RuntimeError("Failed to generate any video clips")

        return clips

    async def _poll_video_operation(
        self,
        operation,
        timeout_seconds: int = 300,
        poll_interval: int = 5,
    ):
        """Poll a video generation operation until completion."""
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            # Check if operation is done
            result = await asyncio.to_thread(operation.result)

            if result is not None:
                return result

            # Wait before polling again
            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Video generation timed out after {timeout_seconds} seconds")

    def _get_dimensions_for_aspect_ratio(self, aspect_ratio: str) -> tuple[int, int]:
        """Get width and height for an aspect ratio."""
        if aspect_ratio == "9:16":
            return 1080, 1920  # Vertical
        elif aspect_ratio == "16:9":
            return 1920, 1080  # Horizontal
        elif aspect_ratio == "1:1":
            return 1080, 1080  # Square
        else:
            return 1080, 1920  # Default to vertical

    def _build_enhanced_prompt(
        self,
        prompt: str,
        style: VeoStyle,
        negative_prompt: str | None,
    ) -> str:
        """Build an enhanced prompt with style modifiers."""
        # Add style modifier
        style_modifier = STYLE_PROMPT_MODIFIERS.get(style, "")
        enhanced = f"{prompt}, {style_modifier}" if style_modifier else prompt

        # Add quality modifiers
        enhanced += ", high quality, professional production"

        # Note: Negative prompts are typically handled differently in video models
        # For now, we'll add them as clarifications
        if negative_prompt:
            enhanced += f", avoid: {negative_prompt}"

        return enhanced

    async def _upload_video_to_storage(
        self,
        video_data: bytes,
        storage_path: str,
    ) -> str:
        """Upload generated video to Supabase storage."""
        url = await asyncio.to_thread(
            self.storage.upload_file,
            BROLL_OUTPUT_BUCKET,
            storage_path,
            video_data,
            content_type="video/mp4",
        )
        return url

    async def get_generation(self, generation_id: uuid.UUID) -> VeoGenerationResponse | None:
        """Get a generation job by ID with its clips."""
        generation = await self._get_generation(generation_id)
        if not generation:
            return None

        # Get clips
        result = await self.db.execute(
            select(GeneratedBRollClip)
            .where(GeneratedBRollClip.generation_id == generation_id)
            .order_by(GeneratedBRollClip.variant_index)
        )
        clips_data = list(result.scalars().all())

        clips = [
            VeoGeneratedClip(
                id=clip.id,
                url=clip.url,
                thumbnail_url=clip.thumbnail_url,
                duration_seconds=clip.duration_seconds,
                width=clip.width,
                height=clip.height,
                file_size_bytes=clip.file_size_bytes,
                variant_index=clip.variant_index,
            )
            for clip in clips_data
        ]

        return VeoGenerationResponse(
            id=generation.id,
            status=VeoGenerationStatus(generation.status),
            prompt=generation.prompt,
            duration_seconds=generation.duration_seconds,
            aspect_ratio=VeoAspectRatio(generation.aspect_ratio),
            style=VeoStyle(generation.style),
            num_variants=generation.num_variants,
            clips=clips,
            error_message=generation.error_message,
            project_id=generation.project_id,
            slot_id=generation.slot_id,
            created_at=generation.created_at,
            completed_at=generation.completed_at,
            generation_time_seconds=generation.generation_time_seconds,
        )

    async def _get_generation(self, generation_id: uuid.UUID) -> GeneratedBRoll | None:
        """Get a generation record from the database."""
        result = await self.db.execute(
            select(GeneratedBRoll).where(GeneratedBRoll.id == generation_id)
        )
        return result.scalar_one_or_none()

    async def regenerate_broll(
        self,
        request: VeoRegenerateRequest,
    ) -> VeoGenerationResponse:
        """
        Regenerate B-Roll based on a previous generation.

        Uses the original parameters but allows overriding specific values.
        """
        # Get the original generation
        original = await self._get_generation(request.original_generation_id)
        if not original:
            raise ValueError(f"Original generation {request.original_generation_id} not found")

        # Create new generation request with merged parameters
        new_request = VeoGenerateRequest(
            prompt=request.prompt or original.prompt,
            duration_seconds=request.duration_seconds or original.duration_seconds,
            aspect_ratio=VeoAspectRatio(original.aspect_ratio),  # Keep original aspect ratio
            style=request.style or VeoStyle(original.style),
            num_variants=request.num_variants or original.num_variants,
            project_id=original.project_id,
            slot_id=original.slot_id,
            negative_prompt=request.negative_prompt or original.negative_prompt,
            seed=None,  # New seed for different results
        )

        return await self.generate_broll(new_request)

    async def list_generations(
        self,
        project_id: uuid.UUID | None = None,
        status: VeoGenerationStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[VeoGenerationResponse], int]:
        """List generation jobs with optional filtering."""
        from sqlalchemy import func

        # Build query
        query = select(GeneratedBRoll)

        if project_id:
            query = query.where(GeneratedBRoll.project_id == project_id)

        if status:
            query = query.where(GeneratedBRoll.status == status.value)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(GeneratedBRoll.created_at.desc()).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        generations = list(result.scalars().all())

        # Build responses
        responses = []
        for gen in generations:
            response = await self.get_generation(gen.id)
            if response:
                responses.append(response)

        return responses, total

    async def delete_generation(self, generation_id: uuid.UUID) -> bool:
        """Delete a generation job and its clips from storage."""
        generation = await self._get_generation(generation_id)
        if not generation:
            return False

        # Get clips to delete from storage
        result = await self.db.execute(
            select(GeneratedBRollClip).where(GeneratedBRollClip.generation_id == generation_id)
        )
        clips = list(result.scalars().all())

        # Delete clips from storage
        for clip in clips:
            if clip.url:
                try:
                    # Extract storage path from URL
                    storage_path = f"generations/{generation_id}/{clip.variant_index}.mp4"
                    await asyncio.to_thread(
                        self.storage.delete_file,
                        BROLL_OUTPUT_BUCKET,
                        storage_path,
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete clip file: {e}")

            # Delete clip record
            await self.db.delete(clip)

        # Delete generation record
        await self.db.delete(generation)
        await self.db.commit()

        logger.info(f"Deleted generation {generation_id} and {len(clips)} clips")
        return True

    async def enhance_prompt(
        self,
        request: PromptEnhancementRequest,
    ) -> PromptEnhancementResponse:
        """
        Enhance a B-Roll prompt using AI to make it more effective.

        Uses Gemini to generate better prompts based on the user's intent.
        """
        # Build the enhancement prompt
        system_prompt = """You are an expert at writing prompts for AI video generation.
        Given a user's description of a B-Roll clip they want, generate 3 enhanced versions
        of their prompt that will produce better, more professional-looking results.

        Each enhanced prompt should:
        1. Be more specific about visual elements
        2. Include cinematography details (camera movement, angle, lighting)
        3. Maintain the user's original intent
        4. Be suitable for marketing/advertising content

        Also recommend which styles (realistic, cinematic, animated, artistic) would work best.

        Respond in JSON format:
        {
            "enhanced_prompts": ["prompt1", "prompt2", "prompt3"],
            "style_recommendations": ["style1", "style2"]
        }
        """

        user_prompt = f"Original prompt: {request.original_prompt}"
        if request.context:
            user_prompt += f"\nContext: {request.context}"
        if request.style_hints:
            user_prompt += f"\nStyle hints: {', '.join(request.style_hints)}"

        try:
            settings = get_settings()
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=settings.veo_prompt_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                ),
            )

            # Parse the response
            import json

            response_text = response.text
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text.strip())

            enhanced_prompts = result.get("enhanced_prompts", [request.original_prompt])
            style_recs = result.get("style_recommendations", [])

            # Map style recommendations to our enum
            mapped_styles = []
            for style in style_recs:
                style_lower = style.lower()
                if "realistic" in style_lower:
                    mapped_styles.append(VeoStyle.REALISTIC)
                elif "cinematic" in style_lower:
                    mapped_styles.append(VeoStyle.CINEMATIC)
                elif "animated" in style_lower or "animation" in style_lower:
                    mapped_styles.append(VeoStyle.ANIMATED)
                elif "artistic" in style_lower or "art" in style_lower:
                    mapped_styles.append(VeoStyle.ARTISTIC)

            return PromptEnhancementResponse(
                original_prompt=request.original_prompt,
                enhanced_prompts=enhanced_prompts[:3],  # Limit to 3
                style_recommendations=mapped_styles[:2],  # Limit to 2
            )

        except Exception as e:
            logger.error(f"Failed to enhance prompt: {e}")
            # Return original prompt on error
            return PromptEnhancementResponse(
                original_prompt=request.original_prompt,
                enhanced_prompts=[request.original_prompt],
                style_recommendations=[VeoStyle.REALISTIC],
            )

    async def select_clip(
        self,
        generation_id: uuid.UUID,
        clip_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> tuple[VeoGeneratedClip, str]:
        """
        Select a generated clip for use in the timeline.

        Copies the clip to permanent project storage and returns the new URL.
        """
        # Get the clip
        result = await self.db.execute(
            select(GeneratedBRollClip).where(
                GeneratedBRollClip.id == clip_id,
                GeneratedBRollClip.generation_id == generation_id,
            )
        )
        clip = result.scalar_one_or_none()

        if not clip or not clip.url:
            raise ValueError(f"Clip {clip_id} not found or has no URL")

        # Download the clip
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(clip.url, follow_redirects=True)
            response.raise_for_status()
            video_data = response.content

        # Upload to project storage (more permanent location)
        storage_path = f"projects/{project_id}/broll/{clip_id}.mp4"
        permanent_url = await asyncio.to_thread(
            self.storage.upload_file,
            "user-uploads",  # Use project uploads bucket
            storage_path,
            video_data,
            content_type="video/mp4",
        )

        clip_response = VeoGeneratedClip(
            id=clip.id,
            url=clip.url,
            thumbnail_url=clip.thumbnail_url,
            duration_seconds=clip.duration_seconds,
            width=clip.width,
            height=clip.height,
            file_size_bytes=clip.file_size_bytes,
            variant_index=clip.variant_index,
        )

        return clip_response, permanent_url
