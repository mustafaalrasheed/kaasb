"""
Kaasb Platform - File Upload Utilities
Handles avatar and file uploads with validation and storage.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

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


def _detect_image_type(header: bytes) -> str | None:
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
    with file_path.open("wb") as f:
        f.write(contents)

    # Return the URL path (relative to static files mount)
    return f"/uploads/avatars/{filename}"


MAX_SERVICE_IMAGES = 5
# Legacy alias — will be removed after all callers migrate to MAX_SERVICE_IMAGES.
MAX_GIG_IMAGES = MAX_SERVICE_IMAGES


async def save_service_image(file: UploadFile, service_id: str) -> str:
    """Save a service image and return the relative URL path.

    Files are still stored under /uploads/gigs/ to avoid rewriting paths for
    existing production images — the on-disk layout is decoupled from the
    domain rename.
    """
    filename_check = file.filename or ""
    if ".." in filename_check or "/" in filename_check or "\\" in filename_check:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_IMAGE_TYPES)}",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    chunks = []
    total_size = 0
    while True:
        chunk = await file.read(64 * 1024)
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

    detected_type = _detect_image_type(contents[:16])
    if detected_type is None or detected_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match a supported image format",
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    filename = f"{service_id}_{uuid.uuid4().hex[:8]}.{ext}"

    service_dir = get_upload_dir("gigs")
    file_path = service_dir / filename
    with file_path.open("wb") as f:
        f.write(contents)

    return f"/uploads/gigs/{filename}"


# Legacy alias.
save_gig_image = save_service_image


# Mirrors the whitelist in schemas/message.py MessageAttachment. Kept
# duplicated because this layer is called outside Pydantic and needs its own
# source of truth for what's acceptable on disk.
_CHAT_ATTACHMENT_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
    "text/plain",
})

# File extensions we'll write to disk. Derived from the MIME whitelist so
# adding a new MIME doesn't accidentally allow an arbitrary extension.
_CHAT_ATTACHMENT_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/zip": "zip",
    "text/plain": "txt",
}


async def save_chat_attachment(
    file: UploadFile, user_id: str
) -> dict:
    """Persist a chat attachment and return the metadata dict the frontend
    passes back to POST /messages/conversations/{id}.

    Validation:
      * filename path-traversal safety (same as avatar/service flows)
      * MIME must be on the chat whitelist (images, PDF, Office docs, zip, txt)
      * size ≤ MAX_UPLOAD_SIZE_MB
      * for image MIMEs, magic bytes must match the claimed type. Non-image
        formats (PDF, Office, zip) skip magic-byte validation because the
        popular office formats share a zip container and false negatives
        would break legitimate uploads. The MIME whitelist + Pydantic
        re-validation on message send give defence in depth.
    """
    filename_check = file.filename or ""
    if ".." in filename_check or "/" in filename_check or "\\" in filename_check:
        raise HTTPException(status_code=400, detail="Invalid filename")

    content_type = (file.content_type or "").lower()
    if content_type not in _CHAT_ATTACHMENT_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Attachment type '{file.content_type}' is not allowed",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(64 * 1024)
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

    # Image-specific magic-byte check: prevents a user claiming
    # content_type="image/png" while uploading an HTML/SVG payload.
    if content_type.startswith("image/"):
        detected = _detect_image_type(contents[:16])
        if detected != content_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match the declared image type",
            )

    ext = _CHAT_ATTACHMENT_EXTENSIONS.get(content_type, "bin")
    filename_out = f"{user_id}_{uuid.uuid4().hex[:12]}.{ext}"
    attach_dir = get_upload_dir("attachments")
    file_path = attach_dir / filename_out
    with file_path.open("wb") as f:
        f.write(contents)

    # The URL matches the static-files mount the frontend uses to render
    # existing avatar/service URLs. filename in the response is the ORIGINAL
    # client-side name so the UI shows "contract.pdf", not the hashed
    # on-disk name.
    return {
        "url": f"/uploads/attachments/{filename_out}",
        "filename": (file.filename or filename_out)[:255],
        "mime_type": content_type,
        "size_bytes": total_size,
    }


def delete_service_image(image_url: str | None) -> None:
    """Delete a service image file from disk (safe against path traversal)."""
    if not image_url:
        return
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    filename = Path(image_url).name
    file_path = (upload_dir / "gigs" / filename).resolve()
    if not str(file_path).startswith(str(upload_dir)):
        return
    if file_path.exists():
        file_path.unlink(missing_ok=True)


# Legacy alias.
delete_gig_image = delete_service_image


def delete_avatar(avatar_url: str | None) -> None:
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
