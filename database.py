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
        self.supabase_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and key are required")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

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

    async def create_user(self, telegram_id: int, username: str = None, 
                         first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """Create or update user in database."""
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

    async def log_product(self, user_id: int, product_name: str) -> Dict[str, Any]:
        """Log a product usage."""
        try:
            # Get user
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            product_data = {
                'user_id': user['id'],
                'product_name': product_name,
                'logged_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.table('product_logs').insert(product_data).execute()
            logger.info(f"Logged product for user {user_id}: {product_name}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error logging product for user {user_id}: {e}")
            raise

    async def log_trigger(self, user_id: int, trigger_name: str) -> Dict[str, Any]:
        """Log a trigger."""
        try:
            # Get user
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            trigger_data = {
                'user_id': user['id'],
                'trigger_name': trigger_name,
                'logged_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.table('trigger_logs').insert(trigger_data).execute()
            logger.info(f"Logged trigger for user {user_id}: {trigger_name}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error logging trigger for user {user_id}: {e}")
            raise

    async def log_symptom(self, user_id: int, symptom_name: str) -> Dict[str, Any]:
        """Log a symptom."""
        try:
            # Get user
            user = await self.get_user_by_telegram_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            symptom_data = {
                'user_id': user['id'],
                'symptom_name': symptom_name,
                'logged_at': datetime.utcnow().isoformat(),
            }

            response = self.client.table('symptom_logs').insert(symptom_data).execute()
            logger.info(f"Logged symptom for user {user_id}: {symptom_name}")
            return response.data[0]

        except Exception as e:
            logger.error(f"Error logging symptom for user {user_id}: {e}")
            raise

    async def save_photo(self, user_id: int, file: File) -> str:
        """Save photo to Supabase storage and return URL."""
        try:
            # Generate unique filename
            file_extension = file.file_path.split('.')[-1] if '.' in file.file_path else 'jpg'
            filename = f"{user_id}_{uuid.uuid4().hex}.{file_extension}"
            
            logger.info(f"[{user_id}] Starting photo download...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
                try:
                    # Timeout for download
                    async with asyncio.timeout(20):
                        await file.download_to_drive(temp_file.name)
                    logger.info(f"[{user_id}] Photo downloaded to temp: {temp_file.name}")
                except asyncio.TimeoutError:
                    logger.error(f"[{user_id}] Timeout while downloading photo")
                    raise

            # Optional: Resize image to reduce file size (comment out if not needed)
            try:
                img = Image.open(temp_file.name)
                img.thumbnail((1024, 1024))  # Resize to 1024px max dimension
                img.save(temp_file.name)
                logger.info(f"[{user_id}] Image resized")
            except Exception as resize_error:
                logger.warning(f"[{user_id}] Could not resize image: {resize_error}")

            logger.info(f"[{user_id}] Uploading to Supabase...")
            with open(temp_file.name, 'rb') as f:
                try:
                    response = self.client.storage.from_('skin-photos').upload(
                        file=f,
                        path=filename,
                        file_options={"content-type": f"image/{file_extension}"}
                    )
                    logger.info(f"[{user_id}] Upload successful: {filename}")
                except Exception as upload_error:
                    logger.error(f"[{user_id}] Error uploading to Supabase: {upload_error}")
                    raise

            # Clean up temp file
            os.unlink(temp_file.name)

            # Get public URL
            public_url = self.client.storage.from_('skin-photos').get_public_url(f"uploads/{filename}")
            logger.info(f"[{user_id}] Public URL: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"[{user_id}] Error saving photo: {e}")
            raise


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