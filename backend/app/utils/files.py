"""
Kaasb Platform - File Upload Utilities
Handles avatar and file uploads with validation and storage.
"""

import uuid
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


_IMAGE_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # WebP starts with RIFF....WEBP
}


def _detect_image_type(header: bytes) -> Optional[str]:
    """Detect image type from magic bytes."""
    for magic, mime in _IMAGE_MAGIC_BYTES.items():
        if header.startswith(magic):
            # WebP needs additional check for "WEBP" at offset 8
            if mime == "image/webp" and header[8:12] != b"WEBP":
                continue
            return mime
    return None


async def save_avatar(file: UploadFile, user_id: str) -> str:
    """
    Save an avatar image and return the relative URL path.
    Validates file type (magic bytes), content type, and size before saving.
    """
    # Reject filenames with path traversal sequences
    filename_check = file.filename or ""
    if ".." in filename_check or "/" in filename_check or "\\" in filename_check:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Validate content type header
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: {', '.join(settings.ALLOWED_IMAGE_TYPES)}",
        )

    # Read file in chunks to avoid loading oversized files into memory
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    chunks = []
    total_size = 0
    while True:
        chunk = await file.read(64 * 1024)  # 64 KB chunks
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
            )
        chunks.append(chunk)
    contents = b"".join(chunks)

    # Validate magic bytes match claimed content type
    detected_type = _detect_image_type(contents[:16])
    if detected_type is None or detected_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match a supported image format",
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
    """Delete an avatar file from disk (safe against path traversal)."""
    if not avatar_url:
        return

    # Only allow deleting files inside the upload directory
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    # Extract just the filename to prevent path traversal
    filename = Path(avatar_url).name
    file_path = (upload_dir / "avatars" / filename).resolve()

    # Ensure resolved path is still within the upload directory
    if not str(file_path).startswith(str(upload_dir)):
        return

    if file_path.exists():
        file_path.unlink(missing_ok=True)
