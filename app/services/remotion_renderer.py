"""Service for rendering videos using Remotion."""

import asyncio
import json
import logging
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.rendered_video import RenderedVideo
from app.schemas.remotion_payload import RemotionPayload
from app.schemas.render import RenderMode, RenderStatus
from app.utils.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)


def _log_payload_preview(render_id: uuid.UUID, payload: dict) -> None:
    """Log a preview of the Remotion payload for debugging."""
    logger.info(f"[RENDER {render_id}] " + "=" * 50)
    logger.info(f"[RENDER {render_id}] PAYLOAD PREVIEW:")
    logger.info(f"[RENDER {render_id}] " + "=" * 50)

    # Basic info
    logger.info(f"[RENDER {render_id}]   Composition: {payload.get('composition_id', 'N/A')}")
    logger.info(f"[RENDER {render_id}]   FPS: {payload.get('fps', 30)}")
    logger.info(
        f"[RENDER {render_id}]   Duration (frames): {payload.get('duration_in_frames', 'N/A')}"
    )

    # Calculate duration in seconds
    fps = payload.get("fps", 30)
    duration_frames = payload.get("duration_in_frames", 0)
    duration_secs = duration_frames / fps if fps else 0
    logger.info(f"[RENDER {render_id}]   Duration (seconds): {duration_secs:.2f}s")

    # Dimensions
    width = payload.get("width", "N/A")
    height = payload.get("height", "N/A")
    logger.info(f"[RENDER {render_id}]   Dimensions: {width}x{height}")

    # Timeline segments
    timeline = payload.get("timeline", [])
    logger.info(f"[RENDER {render_id}]   Timeline segments: {len(timeline)}")

    # Count segment types
    segment_types: dict[str, int] = {}
    for segment in timeline:
        seg_type = segment.get("type", "unknown")
        segment_types[seg_type] = segment_types.get(seg_type, 0) + 1

    if segment_types:
        logger.info(f"[RENDER {render_id}]   Segment breakdown:")
        for seg_type, count in sorted(segment_types.items()):
            logger.info(f"[RENDER {render_id}]     - {seg_type}: {count}")

    # Log first few segments with details
    logger.info(f"[RENDER {render_id}]   First 5 segments:")
    for i, segment in enumerate(timeline[:5]):
        seg_type = segment.get("type", "unknown")
        start_frame = segment.get("start_frame", "?")
        duration = segment.get("duration_frames", "?")

        # Get source info if available
        source_info = ""
        if "source" in segment:
            source = segment["source"]
            if isinstance(source, dict):
                url = source.get("url", "")
                if url:
                    # Truncate long URLs
                    source_info = f" | src: ...{url[-40:]}" if len(url) > 40 else f" | src: {url}"

        logger.info(
            f"[RENDER {render_id}]     [{i}] {seg_type} @ frame {start_frame} "
            f"(dur: {duration}){source_info}"
        )

    if len(timeline) > 5:
        logger.info(f"[RENDER {render_id}]     ... and {len(timeline) - 5} more segments")

    # Audio track
    audio = payload.get("audio_track")
    if audio:
        logger.info(f"[RENDER {render_id}]   Audio track: {audio.get('url', 'N/A')[:50]}...")

    # Brand profile
    brand = payload.get("brand_profile")
    if brand:
        logger.info(f"[RENDER {render_id}]   Brand profile: included")

    logger.info(f"[RENDER {render_id}] " + "=" * 50)


def _log_command(render_id: uuid.UUID, cmd: list[str], cwd: str) -> None:
    """Log the command being executed."""
    logger.info(f"[RENDER {render_id}] " + "-" * 40)
    logger.info(f"[RENDER {render_id}] COMMAND:")
    logger.info(f"[RENDER {render_id}]   Working dir: {cwd}")
    logger.info(f"[RENDER {render_id}]   Command: {' '.join(cmd)}")
    logger.info(f"[RENDER {render_id}] " + "-" * 40)


def _log_process_output(
    render_id: uuid.UUID,
    stdout: bytes,
    stderr: bytes,
    return_code: int,
) -> None:
    """Log stdout and stderr from the render process."""
    logger.info(f"[RENDER {render_id}] " + "-" * 40)
    logger.info(f"[RENDER {render_id}] PROCESS OUTPUT (exit code: {return_code}):")
    logger.info(f"[RENDER {render_id}] " + "-" * 40)

    # Log stdout
    if stdout:
        stdout_text = stdout.decode(errors="replace")
        lines = stdout_text.strip().split("\n")
        logger.info(f"[RENDER {render_id}] STDOUT ({len(lines)} lines):")
        for line in lines[-30:]:  # Last 30 lines
            logger.info(f"[RENDER {render_id}]   {line}")
        if len(lines) > 30:
            logger.info(f"[RENDER {render_id}]   ... ({len(lines) - 30} earlier lines omitted)")
    else:
        logger.info(f"[RENDER {render_id}] STDOUT: (empty)")

    # Log stderr
    if stderr:
        stderr_text = stderr.decode(errors="replace")
        lines = stderr_text.strip().split("\n")
        logger.info(f"[RENDER {render_id}] STDERR ({len(lines)} lines):")
        for line in lines[-20:]:  # Last 20 lines
            logger.info(f"[RENDER {render_id}]   {line}")
        if len(lines) > 20:
            logger.info(f"[RENDER {render_id}]   ... ({len(lines) - 20} earlier lines omitted)")
    else:
        logger.info(f"[RENDER {render_id}] STDERR: (empty)")

    logger.info(f"[RENDER {render_id}] " + "-" * 40)


class RemotionRendererService:
    """Service for rendering videos using Remotion CLI or Lambda."""

    # Path to the remotion project (relative to repo root)
    REMOTION_PROJECT_PATH = "remotion"

    # Output bucket/path for rendered videos
    RENDER_OUTPUT_BUCKET = "rendered-videos"

    def __init__(self, db: AsyncSession):
        """Initialize the renderer service."""
        self.db = db
        self.storage = SupabaseStorage()

    async def create_render_job(
        self,
        project_id: uuid.UUID,
        payload: RemotionPayload,
    ) -> RenderedVideo:
        """Create a new render job in pending status."""
        render = RenderedVideo(
            project_id=project_id,
            composition_id=payload.composition_id.value,
            remotion_payload=payload.model_dump(mode="json"),
            status=RenderStatus.PENDING.value,
        )
        self.db.add(render)
        await self.db.commit()
        await self.db.refresh(render)

        logger.info(f"Created render job {render.id} for project {project_id}")
        return render

    async def get_render(self, render_id: uuid.UUID) -> RenderedVideo | None:
        """Get a render job by ID."""
        result = await self.db.execute(select(RenderedVideo).where(RenderedVideo.id == render_id))
        return result.scalar_one_or_none()

    async def get_project_renders(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[RenderedVideo], int]:
        """Get all renders for a project with pagination."""
        # Count total using SQL COUNT for efficiency
        count_result = await self.db.execute(
            select(func.count())
            .select_from(RenderedVideo)
            .where(RenderedVideo.project_id == project_id)
        )
        total = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(RenderedVideo)
            .where(RenderedVideo.project_id == project_id)
            .order_by(RenderedVideo.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        renders = list(result.scalars().all())

        return renders, total

    async def update_payload(
        self,
        render_id: uuid.UUID,
        payload: RemotionPayload,
    ) -> RenderedVideo | None:
        """Update the payload for a pending render job."""
        render = await self.get_render(render_id)
        if not render:
            return None

        if render.status != RenderStatus.PENDING.value:
            raise ValueError(f"Cannot update payload for render in status: {render.status}")

        render.remotion_payload = payload.model_dump(mode="json")
        render.composition_id = payload.composition_id.value
        await self.db.commit()
        await self.db.refresh(render)

        return render

    async def start_render(
        self,
        render_id: uuid.UUID,
        mode: RenderMode | None = None,
    ) -> RenderedVideo:
        """Start rendering a video.

        If mode is None, automatically selects Lambda if configured, otherwise local.
        """
        render = await self.get_render(render_id)
        if not render:
            raise ValueError(f"Render job {render_id} not found")

        if render.status != RenderStatus.PENDING.value:
            raise ValueError(f"Cannot start render in status: {render.status}")

        # Auto-select mode if not specified
        if mode is None:
            settings = get_settings()
            mode = RenderMode.LAMBDA if settings.remotion_lambda_enabled else RenderMode.LOCAL

        logger.info(f"[RENDER {render_id}] Starting render in {mode.value} mode")

        # Update status to rendering
        render.status = RenderStatus.RENDERING.value
        await self.db.commit()

        try:
            if mode == RenderMode.LOCAL:
                logger.info(f"[RENDER {render_id}] Using LOCAL renderer")
                result = await self._render_local(render)
            else:
                logger.info(f"[RENDER {render_id}] Using LAMBDA renderer")
                result = await self._render_lambda(render)

            # Update with success
            render.status = RenderStatus.COMPLETED.value
            render.video_url = result["video_url"]
            render.thumbnail_url = result.get("thumbnail_url")
            render.duration_seconds = result.get("duration_seconds")
            render.file_size_bytes = result.get("file_size_bytes")
            render.render_time_seconds = result.get("render_time_seconds")

            logger.info(f"Render {render_id} completed successfully")

        except Exception as e:
            # Update with failure
            render.status = RenderStatus.FAILED.value
            logger.error(f"Render {render_id} failed: {e}")
            raise

        finally:
            await self.db.commit()
            await self.db.refresh(render)

        return render

    async def _render_local(self, render: RenderedVideo) -> dict:
        """Render video using local Remotion CLI."""
        start_time = time.time()
        logger.info(f"[RENDER {render.id}] ========== Starting local render ==========")

        # Log payload preview
        _log_payload_preview(render.id, render.remotion_payload)

        # Create temp directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write payload to temp file
            logger.info(f"[RENDER {render.id}] Writing payload to temp file...")
            payload_path = Path(temp_dir) / "payload.json"
            with open(payload_path, "w") as f:
                json.dump(render.remotion_payload, f, indent=2)

            logger.info(f"[RENDER {render.id}] Payload written to: {payload_path}")

            # Output path
            output_filename = f"{render.id}.mp4"
            output_path = Path(temp_dir) / output_filename

            # Build remotion render command
            remotion_dir = Path(self.REMOTION_PROJECT_PATH).absolute()
            composition_id = render.composition_id

            cmd = [
                "npx",
                "remotion",
                "render",
                composition_id,
                str(output_path),
                "--props",
                str(payload_path),
                "--codec",
                "h264",
            ]

            # Log the command
            _log_command(render.id, cmd, str(remotion_dir))

            logger.info(f"[RENDER {render.id}] Executing Remotion CLI...")

            # Run render command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(remotion_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            elapsed = time.time() - start_time
            logger.info(f"[RENDER {render.id}] Remotion CLI finished (elapsed: {elapsed:.1f}s)")

            # Always log process output for debugging
            _log_process_output(render.id, stdout, stderr, process.returncode)

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"[RENDER {render.id}] FAILED with exit code {process.returncode}")
                raise RuntimeError(f"Remotion render failed: {error_msg}")

            # Check output exists
            if not output_path.exists():
                raise RuntimeError("Render completed but output file not found")

            # Get file size
            file_size = output_path.stat().st_size
            logger.info(f"[RENDER {render.id}] Output file size: {file_size / (1024*1024):.2f} MB")

            # Upload to Supabase storage
            logger.info(f"[RENDER {render.id}] Uploading to Supabase storage...")
            video_url = await self._upload_to_storage(
                output_path,
                f"renders/{render.project_id}/{output_filename}",
            )
            upload_elapsed = time.time() - start_time
            logger.info(
                f"[RENDER {render.id}] Upload complete (total elapsed: {upload_elapsed:.1f}s)"
            )

            # Calculate render time
            render_time = time.time() - start_time
            logger.info(
                f"[RENDER {render.id}] ========== RENDER COMPLETE ({render_time:.1f}s) =========="
            )

            # Get duration from payload
            payload = RemotionPayload.model_validate(render.remotion_payload)
            duration_seconds = payload.duration_in_frames / payload.fps

            return {
                "video_url": video_url,
                "thumbnail_url": None,  # TODO: Generate thumbnail
                "duration_seconds": duration_seconds,
                "file_size_bytes": file_size,
                "render_time_seconds": render_time,
            }

    async def _render_lambda(self, render: RenderedVideo) -> dict:
        """Render video using AWS Lambda (Remotion Lambda).

        This method uses the Remotion Lambda API to render videos in AWS.
        The render is triggered via the @remotion/lambda renderMediaOnLambda API.
        """
        settings = get_settings()

        if not settings.remotion_lambda_enabled:
            raise ValueError(
                "Remotion Lambda not configured. "
                "Set REMOTION_AWS_REGION and REMOTION_FUNCTION_NAME in .env"
            )

        start_time = time.time()
        logger.info(f"[RENDER {render.id}] ========== Starting Lambda render ==========")

        # Log payload preview
        _log_payload_preview(render.id, render.remotion_payload)

        # Get the Remotion payload
        payload = RemotionPayload.model_validate(render.remotion_payload)

        # Build the Lambda render request
        lambda_input = self._build_lambda_input(render, payload, settings)

        # Log Lambda configuration
        logger.info(f"[RENDER {render.id}] " + "-" * 40)
        logger.info(f"[RENDER {render.id}] LAMBDA CONFIG:")
        logger.info(f"[RENDER {render.id}]   Region: {settings.remotion_aws_region}")
        logger.info(f"[RENDER {render.id}]   Function: {settings.remotion_function_name}")
        logger.info(
            f"[RENDER {render.id}]   Serve URL: {lambda_input.get('serveUrl', 'N/A')[:60]}..."
        )
        logger.info(f"[RENDER {render.id}]   Composition: {lambda_input.get('composition')}")
        logger.info(f"[RENDER {render.id}]   Codec: {lambda_input.get('codec')}")
        logger.info(
            f"[RENDER {render.id}]   Frames per Lambda: {lambda_input.get('framesPerLambda')}"
        )
        logger.info(f"[RENDER {render.id}] " + "-" * 40)

        # Invoke Lambda and wait for completion
        result = await self._invoke_lambda_render(lambda_input, settings, render.id)

        # Calculate render time
        render_time = time.time() - start_time

        # Download the rendered video and upload to Supabase
        video_url = await self._transfer_lambda_output(
            result["outputUrl"],
            render.project_id,
            render.id,
        )

        duration_seconds = payload.duration_in_frames / payload.fps

        return {
            "video_url": video_url,
            "thumbnail_url": None,  # TODO: Generate thumbnail from Lambda output
            "duration_seconds": duration_seconds,
            "file_size_bytes": result.get("fileSizeBytes"),
            "render_time_seconds": render_time,
        }

    def _build_lambda_input(
        self,
        render: RenderedVideo,
        payload: RemotionPayload,
        settings: Any,
    ) -> dict:
        """Build the input for Remotion Lambda render."""
        serve_url = settings.remotion_serve_url
        if not serve_url:
            # Construct the default serve URL from site name
            region = settings.remotion_aws_region
            site_name = settings.remotion_site_name
            serve_url = (
                f"https://remotionlambda-{region}.s3.{region}.amazonaws.com/"
                f"sites/{site_name}/index.html"
            )

        return {
            "type": "start",
            "serveUrl": serve_url,
            "composition": payload.composition_id.value,
            "inputProps": payload.model_dump(mode="json"),
            "codec": "h264",
            "imageFormat": "jpeg",
            "maxRetries": 1,
            "privacy": "public",
            "framesPerLambda": 20,  # Distribute rendering
            "downloadBehavior": {
                "type": "download",
                "fileName": f"{render.id}.mp4",
            },
            "outName": f"{render.id}.mp4",
            "logLevel": "warn",
        }

    async def _invoke_lambda_render(
        self,
        lambda_input: dict,
        settings: Any,
        db_render_id: uuid.UUID,
    ) -> dict:
        """Invoke Remotion Lambda and poll for completion."""
        import boto3
        from botocore.config import Config

        # Create boto3 client
        boto_config = Config(
            region_name=settings.remotion_aws_region,
            signature_version="v4",
        )

        # Use explicit credentials if provided, otherwise use default credential chain
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            lambda_client = boto3.client(
                "lambda",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                config=boto_config,
            )
            logger.info(f"[RENDER {db_render_id}] Using explicit AWS credentials")
        else:
            lambda_client = boto3.client("lambda", config=boto_config)
            logger.info(f"[RENDER {db_render_id}] Using default AWS credential chain")

        function_name = settings.remotion_function_name

        # Start the render
        logger.info(f"[RENDER {db_render_id}] Invoking Lambda function: {function_name}")

        start_response = await asyncio.to_thread(
            lambda_client.invoke,
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(lambda_input),
        )

        # Parse the response
        response_payload = json.loads(start_response["Payload"].read().decode())

        if "errorMessage" in response_payload:
            logger.error(f"[RENDER {db_render_id}] Lambda invocation failed!")
            logger.error(f"[RENDER {db_render_id}] Error: {response_payload['errorMessage']}")
            if "stackTrace" in response_payload:
                logger.error(f"[RENDER {db_render_id}] Stack trace:")
                for line in response_payload["stackTrace"][:10]:
                    logger.error(f"[RENDER {db_render_id}]   {line}")
            raise RuntimeError(f"Lambda invocation failed: {response_payload['errorMessage']}")

        remotion_render_id = response_payload.get("renderId")
        bucket_name = response_payload.get("bucketName")

        if not remotion_render_id or not bucket_name:
            logger.error(f"[RENDER {db_render_id}] Invalid Lambda response: {response_payload}")
            raise RuntimeError(f"Invalid Lambda response: {response_payload}")

        logger.info(f"[RENDER {db_render_id}] Remotion render started")
        logger.info(f"[RENDER {db_render_id}]   Remotion render ID: {remotion_render_id}")
        logger.info(f"[RENDER {db_render_id}]   Bucket: {bucket_name}")

        # Poll for completion
        progress_input = {
            "type": "status",
            "bucketName": bucket_name,
            "renderId": remotion_render_id,
        }

        max_attempts = 180  # 15 minutes with 5-second intervals
        last_progress = -1
        for attempt in range(max_attempts):
            await asyncio.sleep(5)  # Poll every 5 seconds

            progress_response = await asyncio.to_thread(
                lambda_client.invoke,
                FunctionName=function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(progress_input),
            )

            progress = json.loads(progress_response["Payload"].read().decode())

            if "errorMessage" in progress:
                logger.error(f"[RENDER {db_render_id}] Progress check failed!")
                logger.error(f"[RENDER {db_render_id}] Error: {progress['errorMessage']}")
                raise RuntimeError(f"Progress check failed: {progress['errorMessage']}")

            overall_progress = progress.get("overallProgress", 0)
            progress_pct = int(overall_progress * 100)

            # Log progress every 10% or on completion
            if progress_pct >= last_progress + 10 or progress.get("done"):
                chunks_done = progress.get("chunks", {}).get("done", 0)
                chunks_total = progress.get("chunks", {}).get("total", 0)
                logger.info(
                    f"[RENDER {db_render_id}] Progress: {progress_pct}% "
                    f"(chunks: {chunks_done}/{chunks_total})"
                )
                last_progress = progress_pct

            if progress.get("done"):
                logger.info(f"[RENDER {db_render_id}] ========== Lambda render complete ==========")

                # Get the output URL
                output_url = progress.get("outputFile")
                output_size = progress.get("outputSizeInBytes", 0)

                logger.info(f"[RENDER {db_render_id}] Output URL: {output_url[:80]}...")
                logger.info(
                    f"[RENDER {db_render_id}] Output size: {output_size / (1024*1024):.2f} MB"
                )

                if not output_url:
                    raise RuntimeError("Render completed but no output URL")

                return {
                    "outputUrl": output_url,
                    "fileSizeBytes": output_size,
                    "renderMetadata": progress.get("renderMetadata"),
                }

            if progress.get("fatalErrorEncountered"):
                errors = progress.get("errors", [])
                logger.error(f"[RENDER {db_render_id}] FATAL ERROR in Lambda render!")
                for i, err in enumerate(errors[:5]):
                    logger.error(f"[RENDER {db_render_id}]   Error {i+1}: {err}")
                error_msg = "; ".join(str(e) for e in errors) if errors else "Unknown error"
                raise RuntimeError(f"Render failed: {error_msg}")

        logger.error(f"[RENDER {db_render_id}] Render timed out after {max_attempts * 5} seconds")
        raise RuntimeError(f"Render timed out after {max_attempts * 5} seconds")

    async def _transfer_lambda_output(
        self,
        lambda_output_url: str,
        project_id: uuid.UUID,
        render_id: uuid.UUID,
    ) -> str:
        """Download Lambda output and upload to Supabase storage."""
        logger.info(f"[RENDER {render_id}] Transferring Lambda output to Supabase...")
        logger.info(f"[RENDER {render_id}]   Source: {lambda_output_url[:80]}...")

        # Download from S3
        logger.info(f"[RENDER {render_id}]   Downloading from S3...")
        async with httpx.AsyncClient() as client:
            response = await client.get(lambda_output_url, follow_redirects=True)
            response.raise_for_status()
            video_data = response.content

        logger.info(f"[RENDER {render_id}]   Downloaded {len(video_data) / (1024*1024):.2f} MB")

        # Upload to Supabase
        storage_path = f"renders/{project_id}/{render_id}.mp4"
        logger.info(f"[RENDER {render_id}]   Uploading to Supabase: {storage_path}")

        url = await asyncio.to_thread(
            self.storage.upload_file,
            self.RENDER_OUTPUT_BUCKET,
            storage_path,
            video_data,
            content_type="video/mp4",
        )

        logger.info(f"[RENDER {render_id}]   Upload complete: {url[:60]}...")
        return url

    async def _upload_to_storage(self, file_path: Path, storage_path: str) -> str:
        """Upload rendered video to Supabase storage."""
        with open(file_path, "rb") as f:
            file_data = f.read()

        # Upload to storage
        url = await asyncio.to_thread(
            self.storage.upload_file,
            self.RENDER_OUTPUT_BUCKET,
            storage_path,
            file_data,
            content_type="video/mp4",
        )

        return url

    async def cancel_render(self, render_id: uuid.UUID) -> RenderedVideo | None:
        """Cancel a pending or rendering job."""
        render = await self.get_render(render_id)
        if not render:
            return None

        if render.status == RenderStatus.COMPLETED.value:
            raise ValueError("Cannot cancel completed render")

        render.status = RenderStatus.FAILED.value
        await self.db.commit()
        await self.db.refresh(render)

        logger.info(f"Cancelled render {render_id}")
        return render

    async def delete_render(self, render_id: uuid.UUID) -> bool:
        """Delete a render job and its output files."""
        render = await self.get_render(render_id)
        if not render:
            return False

        # Delete video from storage if exists
        if render.video_url:
            try:
                await asyncio.to_thread(
                    self.storage.delete_file,
                    self.RENDER_OUTPUT_BUCKET,
                    f"renders/{render.project_id}/{render_id}.mp4",
                )
            except Exception as e:
                logger.warning(f"Failed to delete render file: {e}")

        # Delete from database
        await self.db.delete(render)
        await self.db.commit()

        logger.info(f"Deleted render {render_id}")
        return True

    async def get_queue_stats(self) -> dict:
        """Get render queue statistics."""
        from datetime import date

        today = date.today()

        # Count by status using SQL COUNT for efficiency
        pending_result = await self.db.execute(
            select(func.count())
            .select_from(RenderedVideo)
            .where(RenderedVideo.status == RenderStatus.PENDING.value)
        )
        pending_count = pending_result.scalar() or 0

        rendering_result = await self.db.execute(
            select(func.count())
            .select_from(RenderedVideo)
            .where(RenderedVideo.status == RenderStatus.RENDERING.value)
        )
        rendering_count = rendering_result.scalar() or 0

        # Count completed/failed today
        completed_result = await self.db.execute(
            select(func.count())
            .select_from(RenderedVideo)
            .where(
                RenderedVideo.status == RenderStatus.COMPLETED.value,
                func.date(RenderedVideo.created_at) == today,
            )
        )
        completed_today = completed_result.scalar() or 0

        failed_result = await self.db.execute(
            select(func.count())
            .select_from(RenderedVideo)
            .where(
                RenderedVideo.status == RenderStatus.FAILED.value,
                func.date(RenderedVideo.created_at) == today,
            )
        )
        failed_today = failed_result.scalar() or 0

        # Calculate average render time
        avg_render_time = None
        if completed_today > 0:
            avg_result = await self.db.execute(
                select(func.avg(RenderedVideo.render_time_seconds)).where(
                    RenderedVideo.status == RenderStatus.COMPLETED.value,
                    func.date(RenderedVideo.created_at) == today,
                    RenderedVideo.render_time_seconds.isnot(None),
                )
            )
            avg_render_time = avg_result.scalar()

        return {
            "pending_count": pending_count,
            "rendering_count": rendering_count,
            "completed_today": completed_today,
            "failed_today": failed_today,
            "avg_render_time_seconds": avg_render_time,
        }
