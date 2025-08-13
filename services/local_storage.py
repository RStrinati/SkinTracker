"""Local storage service for offline operation."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class LocalStorageService:
    """Handles local storage of analysis results and images."""
    
    def __init__(self, db_path: str = "local_analysis.db"):
        """Initialize local storage with SQLite database."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skin_kpis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    image_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    face_area_px INTEGER,
                    blemish_area_px INTEGER,
                    percent_blemished REAL,
                    face_image_path TEXT,
                    blemish_image_path TEXT,
                    overlay_image_path TEXT,
                    sync_status TEXT DEFAULT 'pending',
                    UNIQUE(user_id, image_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    image_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    analysis_data TEXT,
                    sync_status TEXT DEFAULT 'pending',
                    UNIQUE(user_id, image_id)
                )
            """)

    def store_analysis(self, record: Dict[str, object], analysis_data: Optional[Dict] = None) -> None:
        """Store analysis results locally."""
        with sqlite3.connect(self.db_path) as conn:
            # Store KPIs
            conn.execute("""
                INSERT OR REPLACE INTO skin_kpis (
                    user_id, image_id, timestamp, face_area_px, 
                    blemish_area_px, percent_blemished, face_image_path,
                    blemish_image_path, overlay_image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["user_id"],
                record["image_id"],
                record["timestamp"],
                record["face_area_px"],
                record["blemish_area_px"],
                record["percent_blemished"],
                record["face_image_path"],
                record["blemish_image_path"],
                record["overlay_image_path"]
            ))

            # Store full analysis data if provided
            if analysis_data:
                conn.execute("""
                    INSERT OR REPLACE INTO analysis_queue (
                        user_id, image_id, timestamp, analysis_data
                    ) VALUES (?, ?, ?, ?)
                """, (
                    record["user_id"],
                    record["image_id"],
                    record["timestamp"],
                    json.dumps(analysis_data)
                ))

    def get_pending_syncs(self) -> List[Dict[str, object]]:
        """Get all pending records that need to be synced to cloud."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT k.*, q.analysis_data 
                FROM skin_kpis k 
                LEFT JOIN analysis_queue q 
                    ON k.user_id = q.user_id AND k.image_id = q.image_id
                WHERE k.sync_status = 'pending'
            """)
            return [dict(row) for row in cursor.fetchall()]

    def mark_synced(self, user_id: str, image_id: str) -> None:
        """Mark records as synced to cloud."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE skin_kpis 
                SET sync_status = 'synced' 
                WHERE user_id = ? AND image_id = ?
            """, (user_id, image_id))
            
            conn.execute("""
                UPDATE analysis_queue 
                SET sync_status = 'synced' 
                WHERE user_id = ? AND image_id = ?
            """, (user_id, image_id))

    def get_user_history(
        self, user_id: str, limit: int = 10
    ) -> List[Dict[str, object]]:
        """Get analysis history for a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT k.*, q.analysis_data 
                FROM skin_kpis k 
                LEFT JOIN analysis_queue q 
                    ON k.user_id = q.user_id AND k.image_id = q.image_id
                WHERE k.user_id = ?
                ORDER BY k.timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_records(self, days: int = 30) -> None:
        """Clean up synced records older than specified days."""
        cutoff = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM skin_kpis 
                WHERE sync_status = 'synced' 
                AND timestamp < date(?, '-' || ? || ' days')
            """, (cutoff, days))
            
            conn.execute("""
                DELETE FROM analysis_queue 
                WHERE sync_status = 'synced' 
                AND timestamp < date(?, '-' || ? || ' days')
            """, (cutoff, days))
