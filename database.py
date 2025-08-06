import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid
import tempfile
import aiofiles
from PIL import Image

from supabase import create_client, Client
from telegram import File

# Configure logging
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        self.service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.anon_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')

        if not self.supabase_url:
            raise ValueError("NEXT_PUBLIC_SUPABASE_URL is required")
        if not self.anon_key:
            raise ValueError("NEXT_PUBLIC_SUPABASE_ANON_KEY is required")

        # Use service role key if available, otherwise anon key
        self.supabase_key = self.service_role_key or self.anon_key
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Only try to ensure bucket if we have service role key
        if self.service_role_key:
            self._ensure_photo_bucket()
        else:
            logger.warning("No service role key found. Storage bucket creation will be skipped. Please create 'skin-photos' bucket manually in Supabase Dashboard.")

    def _ensure_photo_bucket(self) -> None:
        """Ensure that the photo storage bucket exists."""
        bucket_name = 'skin-photos'
        try:
            # Try to get the bucket to see if it exists
            self.client.storage.get_bucket(bucket_name)
            logger.info(f"Storage bucket '{bucket_name}' already exists")
        except Exception as get_error:
            logger.info(f"Bucket '{bucket_name}' not found, attempting to create it...")
            # Create the bucket with the same constraints as schema.sql
            try:
                self.client.storage.create_bucket(
                    bucket_name,
                    options={
                        "public": False,
                        "file_size_limit": 10 * 1024 * 1024,  # 10 MB
                        "allowed_mime_types": [
                            "image/jpeg",
                            "image/png",
                            "image/webp",
                        ],
                    },
                )
                logger.info(f"Successfully created storage bucket '{bucket_name}'")
            except Exception as bucket_error:
                logger.error(f"Failed to create storage bucket '{bucket_name}': {bucket_error}")
                logger.error("Please create the 'skin-photos' bucket manually in Supabase Dashboard → Storage")
                raise

    async def initialize(self):
        """Initialize database connection and ensure tables exist."""
        try:
            # Test connection
            response = self.client.table('users').select('id').limit(1).execute()
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def close(self):
        """Close database connection."""
        # Supabase client doesn't need explicit closing
        logger.info("Database connection closed")

    async def create_user(
        self,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        timezone: Optional[str] = None,
        reminder_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update a user in the database.

        The ``users`` table now contains ``timezone`` and
        ``reminder_time`` columns which are used by the reminder
        scheduler.  When creating a new user we fall back to ``UTC`` and
        ``09:00`` respectively.  When updating an existing user these
        fields are only modified if explicitly provided to avoid
        overwriting existing preferences.
        """
        try:
            # Check if user already exists
            existing_user = self.client.table('users').select('*').eq('telegram_id', telegram_id).execute()

            if existing_user.data:
                # Update existing user
                user_data = {
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'updated_at': datetime.utcnow().isoformat()
                }
                # Update reminder settings if provided
                if timezone is not None:
                    user_data['timezone'] = timezone
                if reminder_time is not None:
                    user_data['reminder_time'] = reminder_time

                response = self.client.table('users').update(user_data).eq('telegram_id', telegram_id).execute()
                logger.info(f"Updated user: {telegram_id}")
                return response.data[0]
            else:
                # Create new user
                user_data = {
                    'telegram_id': telegram_id,
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'timezone': timezone or 'UTC',
                    'reminder_time': reminder_time or '09:00',
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                response = self.client.table('users').insert(user_data).execute()
                logger.info(f"Created new user: {telegram_id}")
                return response.data[0]
                
        except Exception as e:
            logger.error(f"Error creating/updating user {telegram_id}: {e}")
            raise

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID."""
        try:
            response = self.client.table('users').select('*').eq('telegram_id', telegram_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None

    async def update_user_reminder(
        self, telegram_id: int, reminder_time: str, timezone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a user's reminder settings."""
        try:
            update_data = {
                'reminder_time': reminder_time,
                'updated_at': datetime.utcnow().isoformat()
            }
            if timezone is not None:
                update_data['timezone'] = timezone

            response = (
                self.client.table('users')
                .update(update_data)
                .eq('telegram_id', telegram_id)
                .execute()
            )
            logger.info(f"Updated reminder time for user {telegram_id} to {reminder_time}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error updating reminder time for user {telegram_id}: {e}")
            raise

    async def get_products(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve products for a user including global ones."""
        try:
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                return []
            response = (
                self.client.table('products')
                .select('*')
                .or_(f'user_id.eq.{user["id"]},is_global.eq.true')
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error retrieving products for user {user_id}: {e}")
            return []

    async def add_product(
        self, user_id: int, name: str, product_type: Optional[str] = None, is_global: bool = False
    ) -> Dict[str, Any]:
        """Add a product definition."""
        try:
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            data = {
                'user_id': user['id'],
                'name': name,
                'type': product_type,
                'is_global': is_global,
            }
            response = self.client.table('products').insert(data).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Error adding product for user {user_id}: {e}")
            raise

    async def get_triggers(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve triggers for a user including global ones."""
        try:
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                return []
            response = (
                self.client.table('triggers')
                .select('*')
                .or_(f'user_id.eq.{user["id"]},is_global.eq.true')
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error retrieving triggers for user {user_id}: {e}")
            return []

    async def add_trigger(
        self, user_id: int, name: str, emoji: Optional[str] = None, is_global: bool = False
    ) -> Dict[str, Any]:
        """Add a trigger definition."""
        try:
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            data = {
                'user_id': user['id'],
                'name': name,
                'emoji': emoji,
                'is_global': is_global,
            }
            response = self.client.table('triggers').insert(data).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Error adding trigger for user {user_id}: {e}")
            raise

    async def get_conditions(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve conditions for a user."""
        try:
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                return []
            response = (
                self.client.table('conditions')
                .select('*')
                .eq('user_id', user['id'])
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Error retrieving conditions for user {user_id}: {e}")
            return []

    async def add_condition(self, user_id: int, name: str, condition_type: str) -> Dict[str, Any]:
        """Add a condition for a user."""
        try:
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            data = {
                'user_id': user['id'],
                'name': name,
                'condition_type': condition_type,
            }
            response = self.client.table('conditions').insert(data).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Error adding condition for user {user_id}: {e}")
            raise

    async def log_product(
        self, user_id: int, product_name: str, notes: Optional[str] = None, effect: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log a product usage."""
        try:
            # Get user
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            product_data = {
                'user_id': user['id'],
                'product_name': product_name,
                'effect': effect,
                'notes': notes,
                'logged_at': datetime.utcnow().isoformat()
            }

            response = self.client.table('product_logs').insert(product_data).execute()
            logger.info(f"Logged product for user {user_id}: {product_name}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error logging product for user {user_id}: {e}")
            raise

    async def log_trigger(
        self, user_id: int, trigger_name: str, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log a trigger."""
        try:
            # Get user
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            trigger_data = {
                'user_id': user['id'],
                'trigger_name': trigger_name,
                'notes': notes,
                'logged_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.table('trigger_logs').insert(trigger_data).execute()
            logger.info(f"Logged trigger for user {user_id}: {trigger_name}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error logging trigger for user {user_id}: {e}")
            raise

    async def log_symptom(
        self, user_id: int, symptom_name: str, severity: int, notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log a symptom."""
        try:
            # Get user
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            symptom_data = {
                'user_id': user['id'],
                'symptom_name': symptom_name,
                'severity': severity,
                'notes': notes,
                'logged_at': datetime.utcnow().isoformat(),
            }

            response = self.client.table('symptom_logs').insert(symptom_data).execute()
            logger.info(f"Logged symptom for user {user_id}: {symptom_name}")
            return response.data[0]

        except Exception as e:
            logger.error(f"Error logging symptom for user {user_id}: {e}")
            raise

    async def save_photo(self, user_id: int, file: File) -> tuple[str, str, str]:
        """Save photo to Supabase storage and return URL, temp path and image ID."""
        # Generate unique filename with user folder for privacy
        file_extension = file.file_path.split('.')[-1] if '.' in file.file_path else 'jpg'
        image_id = uuid.uuid4().hex
        filename = f"uploads/{user_id}/{image_id}.{file_extension}"

        logger.info(f"[{user_id}] Starting photo download...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
            temp_path = temp_file.name
            try:
                # Download file from Telegram
                await file.download_to_drive(temp_path)
                logger.info(f"[{user_id}] Photo downloaded to temp: {temp_path}")
            except Exception as download_error:
                logger.error(f"[{user_id}] Error downloading photo: {download_error}")
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise

        # Optional: Resize image to reduce file size
        try:
            img = Image.open(temp_path)
            img.thumbnail((1024, 1024))  # Resize to 1024px max dimension
            img.save(temp_path, optimize=True, quality=85)
            logger.info(f"[{user_id}] Image resized and optimized")
        except Exception as resize_error:
            logger.warning(f"[{user_id}] Could not resize image: {resize_error}")

        logger.info(f"[{user_id}] Uploading to Supabase storage...")
        try:
            with open(temp_path, 'rb') as f:
                response = self.client.storage.from_('skin-photos').upload(
                    file=f,
                    path=filename,
                    file_options={"content-type": f"image/{file_extension}"}
                )
            logger.info(f"[{user_id}] Upload successful: {filename}")

            # Check if upload was successful
            if hasattr(response, 'error') and response.error:
                logger.error(f"[{user_id}] Supabase upload error: {response.error}")
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise Exception(f"Upload failed: {response.error}")

        except Exception as upload_error:
            logger.error(f"[{user_id}] Error uploading to Supabase: {upload_error}")
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise

        # Get public URL - use the same path as uploaded
        public_url = self.client.storage.from_('skin-photos').get_public_url(filename)
        logger.info(f"[{user_id}] Public URL generated: {public_url}")
        # Caller is responsible for cleaning up temp_path
        return public_url, temp_path, image_id


    async def log_photo(self, user_id: int, photo_url: str, analysis: str = None) -> Dict[str, Any]:
        """Log a photo with optional AI analysis."""
        try:
            # Get user
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            photo_data = {
                'user_id': user['id'],
                'photo_url': photo_url,
                'ai_analysis': analysis,
                'logged_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.table('photo_logs').insert(photo_data).execute()
            logger.info(f"Logged photo for user {user_id}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error logging photo for user {user_id}: {e}")
            raise

    async def get_user_logs(self, user_id: int, days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """Get all user logs from the past N days."""
        try:
            # Get user
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                return {}
            
            # Calculate date threshold
            date_threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get all log types
            product_logs = self.client.table('product_logs')\
                .select('*')\
                .eq('user_id', user['id'])\
                .gte('logged_at', date_threshold)\
                .order('logged_at', desc=True)\
                .execute()
            
            trigger_logs = self.client.table('trigger_logs')\
                .select('*')\
                .eq('user_id', user['id'])\
                .gte('logged_at', date_threshold)\
                .order('logged_at', desc=True)\
                .execute()
            
            symptom_logs = self.client.table('symptom_logs')\
                .select('*')\
                .eq('user_id', user['id'])\
                .gte('logged_at', date_threshold)\
                .order('logged_at', desc=True)\
                .execute()
            
            photo_logs = self.client.table('photo_logs')\
                .select('*')\
                .eq('user_id', user['id'])\
                .gte('logged_at', date_threshold)\
                .order('logged_at', desc=True)\
                .execute()
            
            return {
                'products': product_logs.data,
                'triggers': trigger_logs.data,
                'symptoms': symptom_logs.data,
                'photos': photo_logs.data
            }
            
        except Exception as e:
            logger.error(f"Error getting logs for user {user_id}: {e}")
            return {}

    async def get_user_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get user statistics for the past N days."""
        try:
            logs = await self.get_user_logs(user_id, days)
            
            # Calculate basic stats
            stats = {
                'total_logs': sum(len(log_list) for log_list in logs.values()),
                'product_count': len(logs.get('products', [])),
                'trigger_count': len(logs.get('triggers', [])),
                'symptom_count': len(logs.get('symptoms', [])),
                'photo_count': len(logs.get('photos', [])),
                'most_common_products': self._get_most_common(logs.get('products', []), 'product_name'),
                'most_common_triggers': self._get_most_common(logs.get('triggers', []), 'trigger_name'),
                'most_common_symptoms': self._get_most_common(logs.get('symptoms', []), 'symptom_name'),
                'average_severity': self._calculate_average_severity(logs.get('symptoms', []))
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {e}")
            return {}

    def _get_most_common(self, logs: List[Dict[str, Any]], field: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get most common items from logs."""
        counts = {}
        for log in logs:
            item = log.get(field)
            if item:
                counts[item] = counts.get(item, 0) + 1
        
        # Sort by count and return top items
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [{'name': item[0], 'count': item[1]} for item in sorted_items[:limit]]

    def _calculate_average_severity(self, symptom_logs: List[Dict[str, Any]]) -> float:
        """Calculate average symptom severity."""
        if not symptom_logs:
            return 0.0
        
        total_severity = sum(log.get('severity', 0) for log in symptom_logs)
        return round(total_severity / len(symptom_logs), 2)