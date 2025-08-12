import os
import logging
import tempfile
import uuid
import asyncio
from typing import Tuple

from PIL import Image
from supabase import Client
from telegram import File

logger = logging.getLogger(__name__)

class StorageService:
    """Service layer for interacting with Supabase storage."""

    def __init__(self, client: Client):
        self.client = client

    async def save_photo(self, user_id: int, file: File) -> Tuple[str, str, str]:
        """Save a Telegram photo to Supabase storage.

        Returns the public URL, path to the downloaded temporary file, and
        generated image ID. The caller is responsible for cleaning up the
        temporary file after any additional processing.
        """
        file_extension = file.file_path.split('.')[-1] if '.' in file.file_path else 'jpg'
        image_id = uuid.uuid4().hex
        filename = f"uploads/{user_id}/{image_id}.{file_extension}"

        logger.info("[%s] Starting photo download...", user_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            temp_path = temp_file.name
            try:
                await file.download_to_drive(temp_path)
                logger.info("[%s] Photo downloaded to temp: %s", user_id, temp_path)
            except Exception as download_error:
                logger.error("[%s] Error downloading photo: %s", user_id, download_error)
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise

        try:
            img = Image.open(temp_path)
            img.thumbnail((1024, 1024))
            img.save(temp_path, optimize=True, quality=85)
            logger.info("[%s] Image resized and optimized", user_id)
        except Exception as resize_error:
            logger.warning("[%s] Could not resize image: %s", user_id, resize_error)

        logger.info("[%s] Uploading to Supabase storage...", user_id)
        try:
            bucket = self.client.storage.from_('skin-photos')
            with open(temp_path, 'rb') as f:
                response = await asyncio.to_thread(
                    bucket.upload,
                    filename,
                    f,
                    {"content-type": f"image/{file_extension}"},
                )
            logger.info("[%s] Upload successful: %s", user_id, filename)
            if hasattr(response, 'error') and response.error:
                logger.error("[%s] Supabase upload error: %s", user_id, response.error)
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise Exception(f"Upload failed: {response.error}")
        except Exception as upload_error:
            logger.error("[%s] Error uploading to Supabase: %s", user_id, upload_error)
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise




        public_url = await asyncio.to_thread(bucket.get_public_url, filename)
        logger.info("[%s] Public URL generated: %s", user_id, public_url)
        logger.info("[%s] Temporary file retained for processing: %s", user_id, temp_path)

        return public_url, temp_path, image_id
