"""Service for rendering videos using Remotion."""

import asyncio
import json
import logging
import tempfile
import time
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rendered_video import RenderedVideo
from app.schemas.remotion_payload import RemotionPayload
from app.schemas.render import RenderMode, RenderStatus
from app.utils.supabase_storage import SupabaseStorage

logger = logging.getLogger(__name__)


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
        # Count total
        count_result = await self.db.execute(
            select(RenderedVideo).where(RenderedVideo.project_id == project_id)
        )
        total = len(count_result.scalars().all())

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
        mode: RenderMode = RenderMode.LOCAL,
    ) -> RenderedVideo:
        """Start rendering a video."""
        render = await self.get_render(render_id)
        if not render:
            raise ValueError(f"Render job {render_id} not found")

        if render.status != RenderStatus.PENDING.value:
            raise ValueError(f"Cannot start render in status: {render.status}")

        # Update status to rendering
        render.status = RenderStatus.RENDERING.value
        await self.db.commit()

        try:
            if mode == RenderMode.LOCAL:
                result = await self._render_local(render)
            else:
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

        # Create temp directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write payload to temp file
            payload_path = Path(temp_dir) / "payload.json"
            with open(payload_path, "w") as f:
                json.dump(render.remotion_payload, f)

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

            logger.info(f"Starting local render: {' '.join(cmd)}")

            # Run render command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(remotion_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Remotion render failed: {error_msg}")

            # Check output exists
            if not output_path.exists():
                raise RuntimeError("Render completed but output file not found")

            # Get file size
            file_size = output_path.stat().st_size

            # Upload to Supabase storage
            video_url = await self._upload_to_storage(
                output_path,
                f"renders/{render.project_id}/{output_filename}",
            )

            # Calculate render time
            render_time = time.time() - start_time

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
        """Render video using AWS Lambda (Remotion Lambda)."""
        # TODO: Implement Lambda rendering
        # This would use @remotion/lambda to render in AWS
        raise NotImplementedError("Lambda rendering not yet implemented")

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

        # Count by status
        pending_result = await self.db.execute(
            select(RenderedVideo).where(RenderedVideo.status == RenderStatus.PENDING.value)
        )
        pending_count = len(pending_result.scalars().all())

        rendering_result = await self.db.execute(
            select(RenderedVideo).where(RenderedVideo.status == RenderStatus.RENDERING.value)
        )
        rendering_count = len(rendering_result.scalars().all())

        # Count completed/failed today
        from sqlalchemy import func

        completed_result = await self.db.execute(
            select(RenderedVideo).where(
                RenderedVideo.status == RenderStatus.COMPLETED.value,
                func.date(RenderedVideo.created_at) == today,
            )
        )
        completed_today = len(completed_result.scalars().all())

        failed_result = await self.db.execute(
            select(RenderedVideo).where(
                RenderedVideo.status == RenderStatus.FAILED.value,
                func.date(RenderedVideo.created_at) == today,
            )
        )
        failed_today = len(failed_result.scalars().all())

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
