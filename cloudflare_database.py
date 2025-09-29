"""
Cloudflare D1 Database Adapter for SkinTracker
Replaces the local SQLite database with Cloudflare D1
"""
import json
import time
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class CloudflareD1Database:
    """Database adapter for Cloudflare D1"""
    
    def __init__(self, db_binding=None):
        self.db = db_binding or getattr(globals(), 'cloudflareDB', None)
        if not self.db:
            logger.warning("No D1 database binding available - using fallback mode")
    
    async def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user session from D1 database"""
        if not self.db:
            return None
            
        try:
            query = """
            SELECT user_id, expires_at 
            FROM auth_sessions 
            WHERE token = ? AND expires_at > ?
            """
            current_time = int(time.time())
            
            result = await self.db.prepare(query).bind(token, current_time).first()
            
            if result:
                return {
                    'user_id': result['user_id'],
                    'expires_at': result['expires_at']
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting session from D1: {e}")
            return None
    
    async def create_session(self, token: str, user_id: int, expires_at: int) -> bool:
        """Create new session in D1 database"""
        if not self.db:
            return False
            
        try:
            query = """
            INSERT OR REPLACE INTO auth_sessions (token, user_id, expires_at)
            VALUES (?, ?, ?)
            """
            
            result = await self.db.prepare(query).bind(token, user_id, expires_at).run()
            return result.success
            
        except Exception as e:
            logger.error(f"Error creating session in D1: {e}")
            return False
    
    async def delete_session(self, token: str) -> bool:
        """Delete session from D1 database"""
        if not self.db:
            return False
            
        try:
            query = "DELETE FROM auth_sessions WHERE token = ?"
            result = await self.db.prepare(query).bind(token).run()
            return result.success
            
        except Exception as e:
            logger.error(f"Error deleting session from D1: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of deleted rows"""
        if not self.db:
            return 0
            
        try:
            current_time = int(time.time())
            query = "DELETE FROM auth_sessions WHERE expires_at < ?"
            
            result = await self.db.prepare(query).bind(current_time).run()
            return result.changes or 0
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    async def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences from D1"""
        if not self.db:
            return None
            
        try:
            query = "SELECT settings FROM user_preferences WHERE user_id = ?"
            result = await self.db.prepare(query).bind(user_id).first()
            
            if result and result['settings']:
                return json.loads(result['settings'])
            return None
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return None
    
    async def save_user_preferences(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """Save user preferences to D1"""
        if not self.db:
            return False
            
        try:
            settings_json = json.dumps(settings)
            query = """
            INSERT OR REPLACE INTO user_preferences (user_id, settings, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """
            
            result = await self.db.prepare(query).bind(user_id, settings_json).run()
            return result.success
            
        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
            return False
    
    async def queue_message(self, user_id: int, message_type: str, message_data: Dict[str, Any]) -> bool:
        """Queue a message for background processing"""
        if not self.db:
            return False
            
        try:
            data_json = json.dumps(message_data)
            query = """
            INSERT INTO message_queue (user_id, message_type, message_data)
            VALUES (?, ?, ?)
            """
            
            result = await self.db.prepare(query).bind(user_id, message_type, data_json).run()
            return result.success
            
        except Exception as e:
            logger.error(f"Error queuing message: {e}")
            return False
    
    async def get_pending_messages(self, limit: int = 10) -> list:
        """Get pending messages for processing"""
        if not self.db:
            return []
            
        try:
            query = """
            SELECT id, user_id, message_type, message_data
            FROM message_queue
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT ?
            """
            
            result = await self.db.prepare(query).bind(limit).all()
            messages = []
            
            for row in result.results:
                messages.append({
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'message_type': row['message_type'],
                    'message_data': json.loads(row['message_data'])
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting pending messages: {e}")
            return []
    
    async def mark_message_processed(self, message_id: int, status: str = 'completed') -> bool:
        """Mark a message as processed"""
        if not self.db:
            return False
            
        try:
            query = """
            UPDATE message_queue 
            SET status = ?, processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """
            
            result = await self.db.prepare(query).bind(status, message_id).run()
            return result.success
            
        except Exception as e:
            logger.error(f"Error marking message as processed: {e}")
            return False

# Global instance - will be initialized by the worker
cloudflare_db = None

def get_cloudflare_db() -> CloudflareD1Database:
    """Get the global CloudflareD1Database instance"""
    global cloudflare_db
    if cloudflare_db is None:
        cloudflare_db = CloudflareD1Database()
    return cloudflare_db
