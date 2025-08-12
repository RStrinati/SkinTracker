import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Dict, List, Optional, Any

from telegram import File

from dotenv import load_dotenv
from services.storage import StorageService
from services.supabase import supabase

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.client = supabase.client

        # Service layer instances
        self.storage = StorageService(self.client)
        
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
            response = await asyncio.to_thread(
                self.client.table('users').select('id').limit(1).execute
            )
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
            existing_user = await asyncio.to_thread(
                self.client.table('users').select('*').eq('telegram_id', telegram_id).execute
            )

            if existing_user.data:
                # Update existing user
                user_data = {
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'updated_at': datetime.now(dt_timezone.utc).isoformat()
                }
                # Update reminder settings if provided
                if timezone is not None:
                    user_data['timezone'] = timezone
                if reminder_time is not None:
                    user_data['reminder_time'] = reminder_time

                response = await asyncio.to_thread(
                    self.client.table('users').update(user_data).eq('telegram_id', telegram_id).execute
                )
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
                    'created_at': datetime.now(dt_timezone.utc).isoformat(),
                    'updated_at': datetime.now(dt_timezone.utc).isoformat()
                }
                
                response = await asyncio.to_thread(
                    self.client.table('users').insert(user_data).execute
                )
                logger.info(f"Created new user: {telegram_id}")
                return response.data[0]
                
        except Exception as e:
            logger.error(f"Error creating/updating user {telegram_id}: {e}")
            raise

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID."""
        try:
            response = await asyncio.to_thread(
                self.client.table('users').select('*').eq('telegram_id', telegram_id).execute
            )
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
                'updated_at': datetime.now(dt_timezone.utc).isoformat()
            }
            if timezone is not None:
                update_data['timezone'] = timezone

            response = await asyncio.to_thread(
                self.client
                .table('users')
                .update(update_data)
                .eq('telegram_id', telegram_id)
                .execute
            )
            logger.info(f"Updated reminder time for user {telegram_id} to {reminder_time}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error updating reminder time for user {telegram_id}: {e}")
            raise

    async def get_users_with_reminders(self) -> List[Dict[str, Any]]:
        """Return all users along with their reminder settings."""
        try:
            response = await asyncio.to_thread(
                self.client
                .table('users')
                .select('telegram_id, reminder_time, timezone')
                .execute
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching user reminders: {e}")
            return []

    async def get_products(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve products for a user including global ones."""
        try:
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                return []
            response = await asyncio.to_thread(
                self.client
                .table('products')
                .select('*')
                .or_(f'user_id.eq.{user["id"]},is_global.eq.true')
                .execute
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
            response = await asyncio.to_thread(
                self.client.table('products').insert(data).execute
            )
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
            response = await asyncio.to_thread(
                self.client
                .table('triggers')
                .select('*')
                .or_(f'user_id.eq.{user["id"]},is_global.eq.true')
                .execute
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
            response = await asyncio.to_thread(
                self.client.table('triggers').insert(data).execute
            )
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
            response = await asyncio.to_thread(
                self.client
                .table('conditions')
                .select('*')
                .eq('user_id', user['id'])
                .execute
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
            response = await asyncio.to_thread(
                self.client.table('conditions').insert(data).execute
            )
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
                'logged_at': datetime.now(dt_timezone.utc).isoformat()
            }

            response = await asyncio.to_thread(
                self.client.table('product_logs').insert(product_data).execute
            )
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
                'logged_at': datetime.now(dt_timezone.utc).isoformat()
            }
            
            response = await asyncio.to_thread(
                self.client.table('trigger_logs').insert(trigger_data).execute
            )
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
                'logged_at': datetime.now(dt_timezone.utc).isoformat(),
            }

            response = await asyncio.to_thread(
                self.client.table('symptom_logs').insert(symptom_data).execute
            )
            logger.info(f"Logged symptom for user {user_id}: {symptom_name}")
            return response.data[0]

        except Exception as e:
            logger.error(f"Error logging symptom for user {user_id}: {e}")
            raise

    async def save_photo(self, user_id: int, file: File) -> tuple[str, str, str]:
        """Delegate photo saving to the storage service."""
        return await self.storage.save_photo(user_id, file)


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
                'logged_at': datetime.now(dt_timezone.utc).isoformat()
            }
            
            response = await asyncio.to_thread(
                self.client.table('photo_logs').insert(photo_data).execute
            )
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
            date_threshold = (datetime.now(dt_timezone.utc) - timedelta(days=days)).isoformat()
            
            def fetch_logs(table_name: str):
                return (
                    self.client.table(table_name)
                    .select('*')
                    .eq('user_id', user['id'])
                    .gte('logged_at', date_threshold)
                    .order('logged_at', desc=True)
                    .execute()
                    .data
                )

            product_logs, trigger_logs, symptom_logs, photo_logs = await asyncio.gather(
                asyncio.to_thread(fetch_logs, 'product_logs'),
                asyncio.to_thread(fetch_logs, 'trigger_logs'),
                asyncio.to_thread(fetch_logs, 'symptom_logs'),
                asyncio.to_thread(fetch_logs, 'photo_logs'),
            )

            return {
                'products': product_logs,
                'triggers': trigger_logs,
                'symptoms': symptom_logs,
                'photos': photo_logs
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