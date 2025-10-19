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
        
        # Don't call _ensure_photo_bucket() during init - move to initialize() method
        # This prevents blocking API calls during import
        self._bucket_ensured = False

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
        logger.info(
            "Database.initialize start (supabase_url_set=%s, service_role=%s, railway_env=%s)",
            bool(os.getenv("NEXT_PUBLIC_SUPABASE_URL")),
            bool(self.service_role_key),
            bool(os.getenv("RAILWAY_ENVIRONMENT")),
        )
        try:
            # Test connection
            response = await asyncio.to_thread(
                self.client.table('users').select('id').limit(1).execute
            )
            logger.info("Database connection established successfully")

            # Ensure photo bucket exists (moved from __init__ to prevent blocking during import)
            if not self._bucket_ensured and self.service_role_key:
                logger.info("Ensuring Supabase storage bucket exists")
                await asyncio.to_thread(self._ensure_photo_bucket)
                self._bucket_ensured = True
            elif not self.service_role_key:
                logger.warning("No service role key found. Storage bucket creation will be skipped. Please create 'skin-photos' bucket manually in Supabase Dashboard.")

            logger.info("Database initialization completed")
        except Exception as e:
            logger.exception("Database initialization failed")
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
            logger.exception(f"Error creating/updating user {telegram_id}")
            raise

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID."""
        try:
            response = await asyncio.to_thread(
                self.client.table('users').select('*').eq('telegram_id', telegram_id).execute
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.exception(f"Error getting user {telegram_id}")
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
            logger.exception(f"Error updating reminder time for user {telegram_id}")
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
            logger.exception("Error fetching user reminders")
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

    async def log_daily_mood(self, telegram_id: int, mood_rating: int, mood_description: str) -> bool:
        """Log a daily mood/feeling rating from reminder response."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"User not found for telegram_id: {telegram_id}")
                return False

            user_id = user['id']
            
            # Insert mood log
            result = self.client.table('daily_mood_logs').insert({
                'user_id': user_id,
                'mood_rating': mood_rating,
                'mood_description': mood_description
            }).execute()
            
            logger.info(f"Logged daily mood for user {telegram_id}: {mood_description} ({mood_rating})")
            return True
            
        except Exception as e:
            logger.error(f"Error logging daily mood for user {telegram_id}: {e}")
            return False

    async def get_recent_mood_logs(self, telegram_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent daily mood logs for a user."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []

            user_id = user['id']
            cutoff_date = (datetime.now(dt_timezone.utc) - timedelta(days=days)).isoformat()
            
            def fetch_mood_logs():
                return self.client.table('daily_mood_logs').select('*').eq('user_id', user_id).gte('logged_at', cutoff_date).order('logged_at', desc=True).execute()
            
            result = await asyncio.to_thread(fetch_mood_logs)
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting mood logs for user {telegram_id}: {e}")
            return []

    async def get_mood_stats(self, telegram_id: int, days: int = 30) -> Dict[str, Any]:
        """Get mood statistics for a user."""
        try:
            mood_logs = await self.get_recent_mood_logs(telegram_id, days)
            
            if not mood_logs:
                return {
                    'total_entries': 0,
                    'average_rating': 0,
                    'mood_distribution': {},
                    'trend': 'No data'
                }
            
            # Calculate statistics
            total_entries = len(mood_logs)
            average_rating = sum(log['mood_rating'] for log in mood_logs) / total_entries
            
            # Count mood distribution
            mood_distribution = {}
            for log in mood_logs:
                desc = log['mood_description']
                mood_distribution[desc] = mood_distribution.get(desc, 0) + 1
            
            # Calculate trend (recent vs older entries)
            half_point = total_entries // 2
            if total_entries >= 4:
                recent_avg = sum(log['mood_rating'] for log in mood_logs[:half_point]) / half_point
                older_avg = sum(log['mood_rating'] for log in mood_logs[half_point:]) / (total_entries - half_point)
                
                if recent_avg > older_avg + 0.3:
                    trend = 'Improving'
                elif recent_avg < older_avg - 0.3:
                    trend = 'Declining'
                else:
                    trend = 'Stable'
            else:
                trend = 'Insufficient data'
            
            return {
                'total_entries': total_entries,
                'average_rating': round(average_rating, 2),
                'mood_distribution': mood_distribution,
                'trend': trend
            }
            
        except Exception as e:
            logger.error(f"Error getting mood stats for user {telegram_id}: {e}")
            return {}

    async def update_product_name(self, telegram_id: int, old_name: str, new_name: str) -> bool:
        """Update a product name for a user."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"User not found for telegram_id: {telegram_id}")
                return False

            user_id = user['id']
            
            # Update in products table
            result = self.client.table('products').update({
                'name': new_name
            }).eq('user_id', user_id).eq('name', old_name).execute()
            
            logger.info(f"Updated product name for user {telegram_id}: {old_name} -> {new_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating product name for user {telegram_id}: {e}")
            return False

    async def delete_product(self, telegram_id: int, product_name: str) -> bool:
        """Delete a product for a user."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"User not found for telegram_id: {telegram_id}")
                return False

            user_id = user['id']
            
            # Delete from products table
            result = self.client.table('products').delete().eq('user_id', user_id).eq('name', product_name).execute()
            
            logger.info(f"Deleted product for user {telegram_id}: {product_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting product for user {telegram_id}: {e}")
            return False

    async def delete_all_user_data(self, telegram_id: int, data_types: List[str]) -> Dict[str, bool]:
        """Delete specified types of user data."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"User not found for telegram_id: {telegram_id}")
                return {}

            user_id = user['id']
            results = {}
            
            # Define table mappings
            table_mapping = {
                'photos': 'photo_logs',
                'products': 'product_logs', 
                'triggers': 'trigger_logs',
                'symptoms': 'symptom_logs',
                'moods': 'daily_mood_logs',
                'kpis': 'skin_kpis'
            }
            
            for data_type in data_types:
                if data_type in table_mapping:
                    table_name = table_mapping[data_type]
                    try:
                        self.client.table(table_name).delete().eq('user_id', user_id).execute()
                        results[data_type] = True
                        logger.info(f"Deleted {data_type} data for user {telegram_id}")
                    except Exception as e:
                        logger.error(f"Error deleting {data_type} for user {telegram_id}: {e}")
                        results[data_type] = False
                else:
                    results[data_type] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Error deleting data for user {telegram_id}: {e}")
            return {}

    async def get_data_summary(self, telegram_id: int) -> Dict[str, int]:
        """Get a summary of how much data exists for each type."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return {}

            user_id = user['id']
            
            # Count data in each table
            def count_table_data(table_name):
                result = self.client.table(table_name).select('id', count='exact').eq('user_id', user_id).execute()
                return result.count if hasattr(result, 'count') else len(result.data)
            
            summary = {}
            tables = {
                'photos': 'photo_logs',
                'products': 'product_logs',
                'triggers': 'trigger_logs', 
                'symptoms': 'symptom_logs',
                'moods': 'daily_mood_logs',
                'kpis': 'skin_kpis'
            }
            
            for data_type, table_name in tables.items():
                try:
                    count = await asyncio.to_thread(count_table_data, table_name)
                    summary[data_type] = count
                except Exception as e:
                    logger.error(f"Error counting {data_type}: {e}")
                    summary[data_type] = 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting data summary for user {telegram_id}: {e}")
            return {}

    # ========== NEW UX ENHANCEMENT METHODS ==========

    async def update_user_onboarding_status(self, telegram_id: int, completed: bool) -> bool:
        """Update user's onboarding completion status."""
        try:
            def update_onboarding():
                result = self.client.table('users').update({
                    'onboarding_completed': completed
                }).eq('telegram_id', telegram_id).execute()
                return len(result.data) > 0
            
            return await asyncio.to_thread(update_onboarding)
        except Exception as e:
            logger.error(f"Error updating onboarding status for user {telegram_id}: {e}")
            return False

    async def get_today_logs(self, telegram_id: int) -> Dict[str, int]:
        """Get count of today's logs for a user."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return {}
                
            user_id = user['id']
            today = datetime.now().strftime('%Y-%m-%d')
            
            def count_today_logs():
                results = {}
                
                # Count photos
                try:
                    photo_result = self.client.table('photo_logs').select('id', count='exact').eq('user_id', user_id).gte('logged_at', f'{today}T00:00:00').execute()
                    results['photo_count'] = photo_result.count if hasattr(photo_result, 'count') else len(photo_result.data)
                except Exception as e:
                    logger.error(f"Error counting today's photo_count: {e}")
                    results['photo_count'] = 0
                
                # Count mood logs
                try:
                    mood_result = self.client.table('daily_mood_logs').select('id', count='exact').eq('user_id', user_id).gte('logged_at', f'{today}T00:00:00').execute()
                    results['mood_count'] = mood_result.count if hasattr(mood_result, 'count') else len(mood_result.data)
                except Exception as e:
                    logger.error(f"Error counting today's mood_count: {e}")
                    results['mood_count'] = 0
                
                # Count symptoms
                try:
                    symptom_result = self.client.table('symptom_logs').select('id', count='exact').eq('user_id', user_id).gte('logged_at', f'{today}T00:00:00').execute()
                    results['symptom_count'] = symptom_result.count if hasattr(symptom_result, 'count') else len(symptom_result.data)
                except Exception as e:
                    logger.error(f"Error counting today's symptom_count: {e}")
                    results['symptom_count'] = 0
                
                # Count products
                try:
                    product_result = self.client.table('product_logs').select('id', count='exact').eq('user_id', user_id).gte('logged_at', f'{today}T00:00:00').execute()
                    results['product_count'] = product_result.count if hasattr(product_result, 'count') else len(product_result.data)
                except Exception as e:
                    logger.error(f"Error counting today's product_count: {e}")
                    results['product_count'] = 0
                
                return results
            
            return await asyncio.to_thread(count_today_logs)
            
        except Exception as e:
            logger.error(f"Error getting today's logs for user {telegram_id}: {e}")
            return {}

    async def get_user_areas(self, telegram_id: int) -> List[Dict[str, Any]]:
        """Get user's tracked areas."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
                
            user_id = user['id']
            
            def get_areas():
                result = self.client.table('user_areas').select('*').eq('user_id', user_id).order('created_at').execute()
                return result.data
            
            return await asyncio.to_thread(get_areas)
            
        except Exception as e:
            logger.error(f"Error getting user areas for {telegram_id}: {e}")
            return []

    async def create_user_area(self, telegram_id: int, area_name: str, description: str = None) -> bool:
        """Create a new tracking area for user."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return False
                
            user_id = user['id']
            
            def create_area():
                result = self.client.table('user_areas').insert({
                    'user_id': user_id,
                    'name': area_name,
                    'description': description
                }).execute()
                return len(result.data) > 0
            
            return await asyncio.to_thread(create_area)
            
        except Exception as e:
            logger.error(f"Error creating area {area_name} for user {telegram_id}: {e}")
            return False

    async def get_area_logs(self, telegram_id: int, area_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get logs for a specific area."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
                
            user_id = user['id']
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            def get_logs():
                result = self.client.table('symptom_logs').select('*').eq('user_id', user_id).eq('area', area_name).gte('logged_at', since_date).order('logged_at', desc=True).execute()
                return result.data
            
            return await asyncio.to_thread(get_logs)
            
        except Exception as e:
            logger.error(f"Error getting area logs for {area_name} for user {telegram_id}: {e}")
            return []

    async def get_area_photos(self, telegram_id: int, area_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get photos for a specific area."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
                
            user_id = user['id']
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            def get_photos():
                result = self.client.table('photo_logs').select('*').eq('user_id', user_id).eq('area', area_name).gte('logged_at', since_date).order('logged_at', desc=True).execute()
                return result.data
            
            return await asyncio.to_thread(get_photos)
            
        except Exception as e:
            logger.error(f"Error getting area photos for {area_name} for user {telegram_id}: {e}")
            return []

    # ========== NEW UX ENHANCEMENT METHODS ==========

    async def update_user_onboarding_status(self, telegram_id: int, completed: bool) -> bool:
        """Update user's onboarding completion status."""
        try:
            result = await asyncio.to_thread(
                lambda: self.client.table('users')
                .update({'onboarding_completed': completed})
                .eq('telegram_id', telegram_id)
                .execute()
            )
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error updating onboarding status for user {telegram_id}: {e}")
            return False

    async def get_user_areas(self, telegram_id: int) -> List[Dict]:
        """Get user's tracked areas."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
            
            user_id = user['id']
            
            result = await asyncio.to_thread(
                lambda: self.client.table('user_areas')
                .select('*')
                .eq('user_id', user_id)
                .execute()
            )
            
            # Add recent log count for each area
            areas = result.data
            for area in areas:
                # Get recent log count (last 7 days)
                recent_count = await self._get_area_recent_log_count(user_id, area['name'])
                area['recent_log_count'] = recent_count
                
            return areas
            
        except Exception as e:
            logger.error(f"Error getting user areas for {telegram_id}: {e}")
            return []

    async def get_area_logs(self, telegram_id: int, area_name: str, days: int = 30) -> List[Dict]:
        """Get symptom logs for a specific area."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
            
            user_id = user['id']
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            result = await asyncio.to_thread(
                lambda: self.client.table('symptom_logs')
                .select('*')
                .eq('user_id', user_id)
                .eq('area', area_name)
                .gte('logged_at', since_date)
                .order('logged_at', desc=True)
                .execute()
            )
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting area logs for {area_name}: {e}")
            return []

    async def get_area_photos(self, telegram_id: int, area_name: str, days: int = 30) -> List[Dict]:
        """Get photos for a specific area."""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
            
            user_id = user['id']
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            result = await asyncio.to_thread(
                lambda: self.client.table('photo_logs')
                .select('*')
                .eq('user_id', user_id)
                .eq('area', area_name)
                .gte('logged_at', since_date)
                .order('logged_at', desc=True)
                .execute()
            )
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting area photos for {area_name}: {e}")
            return []

    async def _get_area_recent_log_count(self, user_id: int, area_name: str, days: int = 7) -> int:
        """Get count of recent logs for an area."""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            result = await asyncio.to_thread(
                lambda: self.client.table('symptom_logs')
                .select('id', count='exact')
                .eq('user_id', user_id)
                .eq('area', area_name)
                .gte('logged_at', since_date)
                .execute()
            )
            
            return result.count if hasattr(result, 'count') else len(result.data)
            
        except Exception as e:
            logger.error(f"Error getting recent log count for area {area_name}: {e}")
            return 0
