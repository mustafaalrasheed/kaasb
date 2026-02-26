"""
Kaasb Platform - File Upload Utilities
Handles avatar and file uploads with validation and storage.
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException, status

from app.core.config import get_settings

settings = get_settings()


def get_upload_dir(subfolder: str = "") -> Path:
    """Get or create the upload directory."""
    upload_path = Path(settings.UPLOAD_DIR) / subfolder
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


async def save_avatar(file: UploadFile, user_id: str) -> str:
    """
    Save an avatar image and return the relative URL path.
    Validates file type and size before saving.
    """
    # Validate content type
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: {', '.join(settings.ALLOWED_IMAGE_TYPES)}",
        )

    # Read file and validate size
    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Generate unique filename
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"

    # Save to avatars directory
    avatar_dir = get_upload_dir("avatars")
    file_path = avatar_dir / filename

    # Remove old avatars for this user
    for old_file in avatar_dir.glob(f"{user_id}_*"):
        old_file.unlink(missing_ok=True)

    # Write new file
    with open(file_path, "wb") as f:
        f.write(contents)

    # Return the URL path (relative to static files mount)
    return f"/uploads/avatars/{filename}"


def delete_avatar(avatar_url: Optional[str]) -> None:
    """Delete an avatar file from disk."""
    if not avatar_url:
        return

    # Convert URL path to file path
    relative_path = avatar_url.lstrip("/")
    file_path = Path(relative_path)

    if file_path.exists():
        file_path.unlink(missing_ok=True)
