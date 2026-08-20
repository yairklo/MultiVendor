import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
FORMAT_TO_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}


async def save_image(file: UploadFile, tenant_id: int, subdir: str = "products") -> str:
    """Validates and persists an uploaded image to local disk, returning the
    public URL path it will be served from (see the /uploads StaticFiles
    mount in main.py). Raises HTTPException on anything invalid -- callers
    don't need to re-validate.
    """
    raw = await file.read()
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image exceeds 5MB limit")

    # Decode with Pillow rather than trusting the client-supplied content-type
    # or filename extension -- both are trivially spoofable.
    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw))  # verify() invalidates the handle; reopen to actually use it
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is not a valid image")

    image_format = (image.format or "").upper()
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format '{image_format}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_FORMATS))}",
        )

    ext = FORMAT_TO_EXT[image_format]
    tenant_dir = Path(settings.UPLOAD_DIR) / str(tenant_id) / subdir
    tenant_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{ext}"
    (tenant_dir / filename).write_bytes(raw)

    return f"/uploads/{tenant_id}/{subdir}/{filename}"
