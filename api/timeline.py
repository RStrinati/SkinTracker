"""
Timeline API endpoints for skin tracking visualization.
Provides unified timeline events and analytics insights.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query, HTTPException, Depends
from uuid import UUID
import logging

from database import Database

logger = logging.getLogger(__name__)

# Response DTOs
class TimelineEvent(BaseModel):
    """Unified timeline event model."""
    id: str
    lane: str  # Symptoms, Products, Triggers, Photos, Notes
    title: str
    start: datetime
    end: Optional[datetime] = None
    severity: Optional[int] = None
    tags: Optional[List[str]] = []
    media_url: Optional[str] = None
    details: Optional[str] = None
    source: str  # user or bot

class TimelineResponse(BaseModel):
    """Timeline events response."""
    events: List[TimelineEvent]
    total_count: int
    from_date: datetime
    to_date: datetime

# Router setup
router = APIRouter(prefix="/api/v1/timeline", tags=["timeline"])

async def get_database() -> Database:
    """Database dependency."""
    db = Database()
    await db.initialize()
    return db

async def get_user_from_telegram_id(telegram_id: int, db: Database) -> Dict[str, Any]:
    """Get user record from telegram ID."""
    user = await db.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def parse_timestamp_safe(timestamp_str: str) -> Optional[datetime]:
    """Parse timestamp string safely, ensuring timezone awareness."""
    if not timestamp_str:
        return None
    
    try:
        # Handle different timestamp formats
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        elif '+' not in timestamp_str and timestamp_str.count(':') == 2:
            # Assume UTC if no timezone info
            timestamp_str += '+00:00'
        
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse timestamp: {timestamp_str}")
        return None

@router.get("/events", response_model=TimelineResponse)
async def get_timeline_events(
    telegram_id: int = Query(..., description="Telegram user ID"),
    from_date: Optional[datetime] = Query(None, description="Start date filter"),
    to_date: Optional[datetime] = Query(None, description="End date filter"),
    lanes: Optional[List[str]] = Query(None, description="Lane filters: Symptoms, Products, Triggers, Photos, Notes"),
    min_severity: Optional[int] = Query(None, ge=1, le=5, description="Minimum severity filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Database = Depends(get_database)
):
    """
    Get timeline events for a user with optional filtering.
    
    Returns a paginated list of timeline events from all data sources,
    unified into a consistent format for visualization.
    """
    try:
        # Get user record
        user = await get_user_from_telegram_id(telegram_id, db)
        user_uuid = UUID(user['id'])
        
        # Set default date range if not provided (last 30 days)
        if not to_date:
            to_date = datetime.now(timezone.utc)
        elif to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)
            
        if not from_date:
            from_date = to_date - timedelta(days=30)
        elif from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        
        # Collect events from all tables
        events_data = []
        
        # Get symptoms
        try:
            symptoms_response = db.client.table('symptom_logs').select('*').eq('user_id', str(user_uuid)).execute()
            for s in symptoms_response.data:
                event_time = parse_timestamp_safe(s.get('logged_at'))
                if event_time and from_date <= event_time <= to_date:
                    if not lanes or 'Symptoms' in lanes:
                        if not min_severity or s.get('severity', 0) >= min_severity:
                            events_data.append({
                                'id': s['id'],
                                'lane': 'Symptoms',
                                'title': s.get('symptom_name', 'Unknown symptom'),
                                'start_ts': s['logged_at'],
                                'severity': s.get('severity'),
                                'details': s.get('notes', ''),
                                'source': 'user'
                            })
        except Exception as e:
            logger.error(f"Error fetching symptoms: {e}")
        
        # Get products
        try:
            products_response = db.client.table('product_logs').select('*').eq('user_id', str(user_uuid)).execute()
            for p in products_response.data:
                event_time = parse_timestamp_safe(p.get('logged_at'))
                if event_time and from_date <= event_time <= to_date:
                    if not lanes or 'Products' in lanes:
                        events_data.append({
                            'id': p['id'],
                            'lane': 'Products',
                            'title': p.get('product_name', 'Unknown product'),
                            'start_ts': p['logged_at'],
                            'details': f"{p.get('effect', '')} - {p.get('notes', '')}".strip(' -'),
                            'source': 'user'
                        })
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
        
        # Get triggers
        try:
            triggers_response = db.client.table('trigger_logs').select('*').eq('user_id', str(user_uuid)).execute()
            for t in triggers_response.data:
                event_time = parse_timestamp_safe(t.get('logged_at'))
                if event_time and from_date <= event_time <= to_date:
                    if not lanes or 'Triggers' in lanes:
                        events_data.append({
                            'id': t['id'],
                            'lane': 'Triggers',
                            'title': t.get('trigger_name', 'Unknown trigger'),
                            'start_ts': t['logged_at'],
                            'details': t.get('notes', ''),
                            'source': 'user'
                        })
        except Exception as e:
            logger.error(f"Error fetching triggers: {e}")
        
        # Sort events by timestamp
        events_data.sort(key=lambda x: x['start_ts'], reverse=True)
        
        # Apply pagination
        total_count = len(events_data)
        paginated_events = events_data[offset:offset + limit]
        
        # Convert to TimelineEvent objects
        timeline_events = []
        for event_data in paginated_events:
            try:
                event_start = parse_timestamp_safe(event_data['start_ts'])
                if event_start:
                    timeline_events.append(TimelineEvent(
                        id=event_data['id'],
                        lane=event_data['lane'],
                        title=event_data['title'],
                        start=event_start,
                        severity=event_data.get('severity'),
                        tags=event_data.get('tags', []),
                        media_url=event_data.get('media_url'),
                        details=event_data.get('details', ''),
                        source=event_data.get('source', 'user')
                    ))
            except Exception as e:
                logger.error(f"Error creating timeline event: {e}")
                continue
        
        return TimelineResponse(
            events=timeline_events,
            total_count=total_count,
            from_date=from_date,
            to_date=to_date
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timeline events: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching timeline events: {str(e)}")

@router.get("/insights/triggers")
async def get_trigger_insights(
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: Database = Depends(get_database)
):
    """Get trigger analysis insights."""
    try:
        user = await get_user_from_telegram_id(telegram_id, db)
        # Simple response for now
        return []
    except Exception as e:
        logger.error(f"Error fetching trigger insights: {e}")
        return []

@router.get("/insights/products")
async def get_product_insights(
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: Database = Depends(get_database)
):
    """Get product effectiveness insights."""
    try:
        user = await get_user_from_telegram_id(telegram_id, db)
        # Simple response for now
        return []
    except Exception as e:
        logger.error(f"Error fetching product insights: {e}")
        return []
