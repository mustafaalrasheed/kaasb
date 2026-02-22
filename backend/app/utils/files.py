"""
Kaasb Platform - File Upload Utilities
Handles avatar and file uploads with validation and storage.
"""

import uuid
from pathlib import Path
from typing import Optional

import magic
from fastapi import UploadFile, HTTPException, status

from app.core.config import get_settings

settings = get_settings()

# Allowed MIME types verified against actual file bytes (not just the header)
_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_upload_dir(subfolder: str = "") -> Path:
    """Get or create the upload directory."""
    upload_path = Path(settings.UPLOAD_DIR) / subfolder
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


async def save_avatar(file: UploadFile, user_id: str) -> str:
    """
    Save an avatar image and return the relative URL path.
    Validates file type (by content, not just header) and size before saving.
    """
    # Read file first so we can inspect actual bytes
    contents = await file.read()

    # Validate size
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Validate actual MIME type from file bytes (prevents spoofed Content-Type headers)
    detected_mime = magic.from_buffer(contents, mime=True)
    if detected_mime not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file content (detected: {detected_mime}). Allowed: jpeg, png, webp",
        )

    # Derive extension from the verified MIME type (not the filename)
    _mime_to_ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = _mime_to_ext[detected_mime]
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
    """Delete an avatar file from disk, guarded against path traversal."""
    if not avatar_url:
        return

    upload_root = Path(settings.UPLOAD_DIR).resolve()
    relative_path = avatar_url.lstrip("/")
    # Resolve the target relative to the current working directory, then check
    # it falls inside the upload root.
    file_path = Path(relative_path).resolve()

    if not str(file_path).startswith(str(upload_root)):
        # Refuse to delete anything outside the upload directory
        return

    if file_path.exists():
        file_path.unlink(missing_ok=True)
