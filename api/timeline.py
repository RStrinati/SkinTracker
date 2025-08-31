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
    window_hours: int = Query(24, description="Hours after trigger to look for symptoms"),
    min_pairs: int = Query(2, description="Minimum trigger-symptom pairs needed"),
    db: Database = Depends(get_database)
):
    """Get trigger analysis insights using Python-based analytics."""
    try:
        user = await get_user_from_telegram_id(telegram_id, db)
        user_uuid = UUID(user['id'])
        
        # Get all triggers and symptoms for this user
        triggers_response = db.client.table('trigger_logs').select('*').eq('user_id', str(user_uuid)).execute()
        symptoms_response = db.client.table('symptom_logs').select('*').eq('user_id', str(user_uuid)).execute()
        
        if not triggers_response.data or not symptoms_response.data:
            return []
        
        insights = []
        window_delta = timedelta(hours=window_hours)
        
        # Group triggers by name
        trigger_groups = {}
        for trigger in triggers_response.data:
            trigger_time = parse_timestamp_safe(trigger['logged_at'])
            if trigger_time:
                name = trigger['trigger_name']
                if name not in trigger_groups:
                    trigger_groups[name] = []
                trigger_groups[name].append(trigger_time)
        
        # Group symptoms by name
        symptom_groups = {}
        for symptom in symptoms_response.data:
            symptom_time = parse_timestamp_safe(symptom['logged_at'])
            if symptom_time:
                name = symptom['symptom_name']
                if name not in symptom_groups:
                    symptom_groups[name] = []
                symptom_groups[name].append(symptom_time)
        
        # Analyze trigger-symptom correlations
        for trigger_name, trigger_times in trigger_groups.items():
            for symptom_name, symptom_times in symptom_groups.items():
                # Count symptoms that occurred within window after triggers
                pair_count = 0
                for trigger_time in trigger_times:
                    for symptom_time in symptom_times:
                        if trigger_time < symptom_time <= trigger_time + window_delta:
                            pair_count += 1
                            break  # Count only one symptom per trigger instance
                
                if pair_count >= min_pairs:
                    # Calculate statistics
                    total_triggers = len(trigger_times)
                    total_symptoms = len(symptom_times)
                    total_events = len(triggers_response.data) + len(symptoms_response.data)
                    
                    if total_triggers > 0 and total_events > 0:
                        confidence = pair_count / total_triggers
                        baseline = total_symptoms / total_events if total_events > 0 else 0
                        lift = confidence / baseline if baseline > 0 else 0
                        
                        # Consider it a likely trigger if confidence > 30% and lift > 1.2
                        is_likely = confidence > 0.3 and lift > 1.2
                        
                        insights.append({
                            "trigger_name": trigger_name,
                            "symptom_name": symptom_name,
                            "pair_count": pair_count,
                            "trigger_count": total_triggers,
                            "symptom_count": total_symptoms,
                            "confidence": round(confidence, 3),
                            "baseline": round(baseline, 3),
                            "lift": round(lift, 2),
                            "is_likely_trigger": is_likely
                        })
        
        # Sort by lift (most significant first)
        insights.sort(key=lambda x: x['lift'], reverse=True)
        return insights[:10]  # Return top 10
        
    except Exception as e:
        logger.error(f"Error fetching trigger insights: {e}")
        return []

@router.get("/insights/products")
async def get_product_insights(
    telegram_id: int = Query(..., description="Telegram user ID"),
    min_events: int = Query(2, description="Minimum product usage events needed"),
    db: Database = Depends(get_database)
):
    """Get product effectiveness insights using Python-based analytics."""
    try:
        user = await get_user_from_telegram_id(telegram_id, db)
        user_uuid = UUID(user['id'])
        
        # Get all product logs and symptoms for this user
        products_response = db.client.table('product_logs').select('*').eq('user_id', str(user_uuid)).execute()
        symptoms_response = db.client.table('symptom_logs').select('*').eq('user_id', str(user_uuid)).execute()
        
        if not products_response.data:
            return []
        
        insights = []
        
        # Group products by name
        product_groups = {}
        for product in products_response.data:
            product_time = parse_timestamp_safe(product['logged_at'])
            if product_time:
                name = product['product_name']
                if name not in product_groups:
                    product_groups[name] = []
                product_groups[name].append({
                    'time': product_time,
                    'effect': product.get('effect', ''),
                    'notes': product.get('notes', '')
                })
        
        # Get symptoms data for correlation analysis
        symptoms_data = []
        for symptom in symptoms_response.data:
            symptom_time = parse_timestamp_safe(symptom['logged_at'])
            if symptom_time:
                symptoms_data.append({
                    'time': symptom_time,
                    'severity': symptom.get('severity', 0),
                    'name': symptom['symptom_name']
                })
        
        # Analyze each product's effectiveness
        for product_name, product_events in product_groups.items():
            if len(product_events) >= min_events:
                # Calculate improvement metrics
                improvements = []
                
                for product_event in product_events:
                    # Look for symptoms in 7-day window before and after product use
                    before_window = product_event['time'] - timedelta(days=7)
                    after_window = product_event['time'] + timedelta(days=7)
                    
                    before_symptoms = [s for s in symptoms_data if before_window <= s['time'] < product_event['time']]
                    after_symptoms = [s for s in symptoms_data if product_event['time'] < s['time'] <= after_window]
                    
                    if before_symptoms and after_symptoms:
                        avg_before = sum(s['severity'] for s in before_symptoms) / len(before_symptoms)
                        avg_after = sum(s['severity'] for s in after_symptoms) / len(after_symptoms)
                        improvement = avg_before - avg_after  # Positive = improvement
                        improvements.append(improvement)
                
                if improvements:
                    avg_improvement = sum(improvements) / len(improvements)
                    
                    # Categorize effectiveness
                    if avg_improvement > 0.5:
                        category = "working"
                    elif avg_improvement < -0.5:
                        category = "worsening" 
                    else:
                        category = "neutral"
                    
                    insights.append({
                        "product_name": product_name,
                        "n_events": len(product_events),
                        "avg_improvement": round(avg_improvement, 2),
                        "median_delta": round(avg_improvement, 2),  # Simplified for now
                        "effectiveness_category": category
                    })
        
        # Sort by effectiveness (most helpful first)
        insights.sort(key=lambda x: x['avg_improvement'], reverse=True)
        return insights[:10]  # Return top 10
        
    except Exception as e:
        logger.error(f"Error fetching product insights: {e}")
        return []
