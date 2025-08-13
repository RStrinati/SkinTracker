import os
import logging
import tempfile
import uuid
import asyncio
import traceback
from typing import Tuple

from PIL import Image
from supabase import Client
from telegram import File

from services.supabase import supabase

logger = logging.getLogger(__name__)


class StorageService:
    """Service layer for interacting with Supabase storage."""

    def __init__(self, client: Client | None = None):
        # Allow injection of a client for testing; fall back to shared service.
        self.client = client or supabase.client

    async def save_photo(self, user_id: int, file: File) -> Tuple[str, str, str]:
        """Save a Telegram photo to Supabase storage.

        Args:
            user_id: The user's Telegram ID
            file: The Telegram File object representing the photo

        Returns:
            Tuple containing:
            - public_url: The Supabase storage URL for the uploaded image
            - temp_path: Path to the temporary file (caller must delete)
            - image_id: Unique ID assigned to this image

        Raises:
            - IOError: If there are file handling errors
            - ValueError: If the image format is invalid
            - Exception: For Supabase upload errors
        """
        file_extension = file.file_path.split('.')[-1] if '.' in file.file_path else 'jpg'
        image_id = uuid.uuid4().hex
        filename = f"uploads/{user_id}/{image_id}.{file_extension}"
        temp_path = None

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
                temp_path = temp_file.name
            logger.info("[%s] Created temp file: %s", user_id, temp_path)

            # Download the file
            await file.download_to_drive(temp_path)
            logger.info("[%s] Photo downloaded to temp: %s", user_id, temp_path)

            # Process the image
            with Image.open(temp_path) as img:
                # Calculate new dimensions preserving aspect ratio
                width, height = img.size
                max_size = 1024
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                
                # Use LANCZOS resampling for better quality
                resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                resized.save(temp_path, format=img.format or 'JPEG', optimize=True, quality=85)
                logger.info("[%s] Image resized from %dx%d to %dx%d", 
                          user_id, width, height, new_width, new_height)

            # Upload to Supabase
            logger.info("[%s] Uploading to Supabase storage...", user_id)
            bucket = self.client.storage.from_('skin-photos')
            with open(temp_path, 'rb') as f:
                response = await asyncio.to_thread(
                    bucket.upload,
                    filename,
                    f,
                    {"content-type": f"image/{file_extension}"},
                )

            # Check for upload errors
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Upload failed: {response.error}")

            logger.info("[%s] Upload successful: %s", user_id, filename)
            public_url = await asyncio.to_thread(bucket.get_public_url, filename)
            logger.info("[%s] Public URL generated: %s", user_id, public_url)

            return public_url, temp_path, image_id

        except Exception as e:
            error_msg = f"Error processing photo: {str(e)}"
            logger.error("[%s] %s\n%s", user_id, error_msg, traceback.format_exc())
            
            # Clean up temp file if it exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.info("[%s] Cleaned up temp file after error: %s", user_id, temp_path)
                except Exception as cleanup_error:
                    logger.warning("[%s] Failed to clean up temp file: %s", user_id, cleanup_error)
            
            # Re-raise appropriate error
            if isinstance(e, (IOError, ValueError)):
                raise
            else:
                raise Exception(f"Failed to process photo: {str(e)}")
