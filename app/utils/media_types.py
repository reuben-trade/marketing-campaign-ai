"""Shared media type definitions and utilities."""

from typing import Literal

# Image file types
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Video file types
VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "avi", "m4v", "mkv"}
VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
    "video/x-m4v",
    "video/x-matroska",
}

# File size limits (in bytes)
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB
MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024  # 100MB


def get_media_type(filename: str, content_type: str | None) -> Literal["image", "video"] | None:
    """Determine if file is image or video based on extension and MIME type."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension in IMAGE_EXTENSIONS or content_type in IMAGE_MIME_TYPES:
        return "image"
    elif extension in VIDEO_EXTENSIONS or content_type in VIDEO_MIME_TYPES:
        return "video"

    return None


def is_video_file(filename: str, content_type: str | None) -> bool:
    """Check if file is a supported video format."""
    return get_media_type(filename, content_type) == "video"


def is_image_file(filename: str, content_type: str | None) -> bool:
    """Check if file is a supported image format."""
    return get_media_type(filename, content_type) == "image"


def get_video_content_type(filename: str, provided_content_type: str | None) -> str:
    """Get the content type for a video file."""
    if provided_content_type and provided_content_type in VIDEO_MIME_TYPES:
        return provided_content_type

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    extension_to_mime = {
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "webm": "video/webm",
        "avi": "video/x-msvideo",
        "m4v": "video/x-m4v",
        "mkv": "video/x-matroska",
    }
    return extension_to_mime.get(extension, "video/mp4")
