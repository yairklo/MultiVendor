import asyncio
import io
import re
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
FORMAT_TO_EXT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}

MAX_DIGITAL_FILE_BYTES = 25 * 1024 * 1024
ZIP_EXTS = {"zip", "epub", "docx"}


@lru_cache(maxsize=1)
def _s3_client():
    # Cached: building a boto3 client does a small amount of config
    # resolution work we don't want repeated on every single upload.
    # lru_cache rather than a module-level global so tests can clear it
    # (`_s3_client.cache_clear()`) after monkeypatching settings.
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
    )


async def _persist(raw: bytes, tenant_id: int, subdir: str, filename: str) -> str:
    """Writes a file to whichever backend STORAGE_TYPE selects and returns
    the public URL it's reachable at. Shared by save_image and
    save_digital_file so there's exactly one place that knows about the two
    backends.
    """
    key = f"{tenant_id}/{subdir}/{filename}"

    if settings.STORAGE_TYPE == "s3":
        if not settings.S3_BUCKET or not settings.S3_PUBLIC_URL_BASE:
            raise RuntimeError("STORAGE_TYPE=s3 requires S3_BUCKET and S3_PUBLIC_URL_BASE to be set")
        # boto3 is synchronous (blocking network I/O); run it off the event
        # loop so one upload doesn't stall every other request, same
        # reasoning as the Stripe provider's asyncio.to_thread calls.
        await asyncio.to_thread(_s3_client().put_object, Bucket=settings.S3_BUCKET, Key=key, Body=raw)
        return f"{settings.S3_PUBLIC_URL_BASE.rstrip('/')}/{key}"

    tenant_dir = Path(settings.UPLOAD_DIR) / str(tenant_id) / subdir
    tenant_dir.mkdir(parents=True, exist_ok=True)
    (tenant_dir / filename).write_bytes(raw)
    return f"/uploads/{key}"


async def save_image(file: UploadFile, tenant_id: int, subdir: str = "products") -> str:
    """Validates and persists an uploaded image via _persist (local disk or
    S3-compatible bucket, per STORAGE_TYPE), returning its public URL.
    Raises HTTPException on anything invalid -- callers don't need to
    re-validate.
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
    filename = f"{uuid.uuid4().hex}.{ext}"
    return await _persist(raw, tenant_id, subdir, filename)


def _digital_file_ext(raw: bytes, original_name: str) -> str:
    if raw.startswith(b"%PDF"):
        return "pdf"
    if raw.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        given = Path(original_name or "").suffix.lower().lstrip(".")
        if given in ZIP_EXTS:
            return given
        return "zip"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file type. Upload a PDF, ZIP, EPUB, or Word document.",
    )


def _safe_stem(original_name: str) -> str:
    stem = Path(original_name or "file").stem
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", stem).strip(".-")[:40]
    return cleaned or "file"


async def save_digital_file(file: UploadFile, tenant_id: int, subdir: str = "files") -> str:
    """Persists a seller-uploaded digital good (PDF/ZIP/EPUB/DOCX) via _persist
    and returns its public URL. Magic-bytes, not the client filename, decide
    the type — HTML/JS/executables are rejected.
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")
    if len(raw) > MAX_DIGITAL_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 25MB limit")

    head = raw[:64].lstrip().lower()
    if head.startswith(b"<") or head.startswith(b"<!doctype") or raw.startswith(b"MZ"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

    ext = _digital_file_ext(raw, file.filename or "")
    filename = f"{uuid.uuid4().hex}_{_safe_stem(file.filename or 'file')}.{ext}"
    return await _persist(raw, tenant_id, subdir, filename)
