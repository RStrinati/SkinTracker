"""Message queue service for handling offline messaging."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

class MessageQueueService:
    """Handles queueing and sending of messages when offline."""
    
    def __init__(self, db_path: str = "message_queue.db"):
        """Initialize message queue with SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    media_paths TEXT,
                    timestamp TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    error TEXT
                )
            """)

    def queue_message(
        self,
        user_id: str,
        message_type: str,
        content: str,
        media_paths: Optional[List[str]] = None
    ) -> int:
        """Queue a message for sending."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO message_queue (
                    user_id, message_type, content, media_paths, timestamp
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                message_type,
                content,
                json.dumps(media_paths) if media_paths else None,
                datetime.now().isoformat()
            ))
            return cursor.lastrowid

    def get_pending_messages(self, limit: int = 10) -> List[Dict]:
        """Get pending messages that need to be sent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM message_queue
                WHERE status = 'pending'
                AND retry_count < 3
                ORDER BY timestamp ASC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def mark_sent(self, message_id: int) -> None:
        """Mark a message as successfully sent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE message_queue
                SET status = 'sent'
                WHERE id = ?
            """, (message_id,))

    def mark_failed(self, message_id: int, error: str) -> None:
        """Mark a message as failed with error details."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE message_queue
                SET retry_count = retry_count + 1,
                    error = ?,
                    status = CASE 
                        WHEN retry_count + 1 >= 3 THEN 'failed'
                        ELSE 'pending'
                    END
                WHERE id = ?
            """, (error, message_id))

    def cleanup_old_messages(self, days: int = 7) -> None:
        """Clean up old sent and failed messages."""
        cutoff = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM message_queue
                WHERE status IN ('sent', 'failed')
                AND timestamp < date(?, '-' || ? || ' days')
            """, (cutoff, days))
