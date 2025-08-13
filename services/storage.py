import os
import logging
import tempfile
import uuid
import asyncio
from typing import Tuple, Optional

from PIL import Image, ImageOps
from supabase import Client
from telegram import File

from services.supabase import supabase

logger = logging.getLogger(__name__)


def _mime_from_pil_format(fmt: Optional[str]) -> str:
    """Map PIL image format to a MIME string."""
    fmt = (fmt or "JPEG").upper()
    if fmt == "JPG":
        fmt = "JPEG"
    return {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "TIFF": "image/tiff",
        "BMP": "image/bmp",
    }.get(fmt, "image/jpeg")


def _ext_from_pil_format(fmt: Optional[str]) -> str:
    fmt = (fmt or "JPEG").upper()
    if fmt == "JPG":
        fmt = "JPEG"
    return {
        "JPEG": "jpg",
        "PNG": "png",
        "WEBP": "webp",
        "TIFF": "tif",
        "BMP": "bmp",
    }.get(fmt, "jpg")


class StorageService:
    """Service layer for interacting with Supabase storage."""

    def __init__(self, client: Optional[Client] = None):
        # Allow injection of a client for testing; fall back to shared service.
        self.client: Client = client or supabase.client

    async def save_photo(self, user_id: int, file: File) -> Tuple[str, str, str]:
        """Save a Telegram photo to Supabase storage.

        Args:
            user_id: The user's Telegram ID.
            file: The Telegram File object representing the photo.

        Returns:
            (public_url, temp_path, image_id)

        Raises:
            Exception: For download or Supabase upload errors.
        """
        # Derive an initial extension from Telegram, fallback to jpg.
        raw_path = getattr(file, "file_path", "") or ""
        initial_ext = raw_path.rsplit(".", 1)[-1].lower() if "." in raw_path else "jpg"

        image_id = uuid.uuid4().hex

        logger.info("[%s] Starting photo download...", user_id)

        # Create a temporary file (keep it; caller will delete after later processing).
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{initial_ext}") as tmp:
            temp_path = tmp.name

        # 1) Download from Telegram
        try:
            await file.download_to_drive(custom_path=temp_path)
            logger.info("[%s] Photo downloaded to temp: %s", user_id, temp_path)
        except Exception as dl_err:
            logger.exception("[%s] Error downloading Telegram file", user_id)
            # Ensure we don't leak temp files if download fails
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise dl_err

        # 2) Resize / normalize (in a worker thread; don't block the loop)
        async def _process_image(path: str) -> tuple[str, str]:
            try:
                with Image.open(path) as img:
                    # Correct orientation based on EXIF
                    img = ImageOps.exif_transpose(img)

                    width, height = img.size
                    max_size = 1024
                    if max(width, height) > max_size:
                        if width >= height:
                            new_w = max_size
                            new_h = int(height * (max_size / width))
                        else:
                            new_h = max_size
                            new_w = int(width * (max_size / height))
                        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        logger.info("[%s] Image resized from %dx%d to %dx%d",
                                    user_id, width, height, new_w, new_h)
                    else:
                        new_w, new_h = width, height
                        logger.info("[%s] Image kept at original size %dx%d",
                                    user_id, width, height)

                    # Preserve format when possible; default to JPEG
                    save_fmt = img.format or "JPEG"

                    # JPEG-specific quality; PNG ignores it
                    save_kwargs = {"optimize": True}
                    if save_fmt.upper() == "JPEG":
                        save_kwargs["quality"] = 85
                        save_kwargs["progressive"] = True

                    img.save(path, format=save_fmt, **save_kwargs)
                    return save_fmt, _mime_from_pil_format(save_fmt)
            except Exception as e:
                logger.exception("[%s] Error during image processing; using original", user_id)
                # If we failed to re-save, fall back to default MIME guess
                return None, f"image/{initial_ext if initial_ext != 'jpg' else 'jpeg'}"

        save_format, mime_type = await asyncio.to_thread(_process_image, temp_path)
        final_ext = _ext_from_pil_format(save_format) if save_format else (initial_ext or "jpg")

        # 3) Upload to Supabase (bucket must exist and be public or use signed URLs)
        bucket = self.client.storage.from_("skin-photos")
        # Keep the on-bucket name consistent with the final encoding
        filename = f"uploads/{user_id}/{image_id}.{final_ext}"

        logger.info("[%s] Uploading to Supabase storage: %s", user_id, filename)
        try:
            with open(temp_path, "rb") as f:
                # supabase-py raises on error; file_options uses camelCase like the JS client
                await asyncio.to_thread(
                    bucket.upload,
                    filename,
                    f,
                    {"contentType": mime_type, "upsert": False},
                )
            logger.info("[%s] Upload successful: %s", user_id, filename)
        except Exception as upload_error:
            logger.error("[%s] Error uploading to Supabase: %s", user_id, upload_error)
            # Clean up temp on failure (since caller won't need it)
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise

        # 4) Public URL (requires bucket or file to be public; otherwise use signed URL)
        public_url = await asyncio.to_thread(bucket.get_public_url, filename)
        logger.info("[%s] Public URL generated: %s", user_id, public_url)
        logger.info("[%s] Temporary file retained for processing: %s", user_id, temp_path)

        return public_url, temp_path, image_id
