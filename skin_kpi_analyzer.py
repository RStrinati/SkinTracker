"""
Skin KPIs Analysis and Progress Tracking

This module demonstrates how to query and analyze skin health KPIs from the database.
The skin_kpis table stores quantitative metrics from photo analysis that can be used
to track skin health progress over time.

KPIs Tracked:
- face_area_px: Total face area detected in pixels
- blemish_area_px: Total area of detected blemishes in pixels  
- percent_blemished: Percentage of face area with blemishes (0-100)
- Analysis visualization images (face, blemish, overlay)

Use Cases:
1. Progress tracking: Compare percent_blemished over time
2. Treatment effectiveness: Correlate improvements with product logs
3. Trigger analysis: Compare KPIs around trigger events
4. Severity assessment: Track blemish area trends
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import asyncio
import logging

logger = logging.getLogger(__name__)

class SkinKPIAnalyzer:
    """Analyzes skin health KPIs and provides progress insights."""
    
    def __init__(self, database):
        self.db = database
    
    async def get_user_kpis(self, telegram_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get all skin KPIs for a user in the last N days."""
        try:
            # Get user UUID from telegram_id
            user = await self.db.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
            
            # Calculate date threshold
            date_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            # Query skin KPIs
            response = await asyncio.to_thread(
                self.db.client.table('skin_kpis')
                .select('*')
                .eq('user_id', user['id'])
                .gte('timestamp', date_threshold)
                .order('timestamp', desc=True)
                .execute
            )
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting KPIs for user {telegram_id}: {e}")
            return []
    
    async def get_progress_summary(self, telegram_id: int, days: int = 30) -> Dict[str, Any]:
        """Get a progress summary showing improvement trends."""
        kpis = await self.get_user_kpis(telegram_id, days)
        
        if len(kpis) < 2:
            return {"message": "Need at least 2 photos to show progress"}
        
        # Sort by timestamp (newest first)
        kpis.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Compare latest vs earliest
        latest = kpis[0]
        earliest = kpis[-1]
        
        # Calculate improvements
        blemish_change = latest['percent_blemished'] - earliest['percent_blemished']
        face_area_change = latest['face_area_px'] - earliest['face_area_px']
        
        return {
            "total_photos": len(kpis),
            "date_range": {
                "start": earliest['timestamp'],
                "end": latest['timestamp']
            },
            "blemish_improvement": {
                "current_percent": round(latest['percent_blemished'], 2),
                "initial_percent": round(earliest['percent_blemished'], 2),
                "change": round(-blemish_change, 2),  # Negative change is improvement
                "improved": blemish_change < 0
            },
            "face_area": {
                "current_px": latest['face_area_px'],
                "initial_px": earliest['face_area_px'],
                "change_px": face_area_change
            },
            "average_blemish_percent": round(
                sum(k['percent_blemished'] for k in kpis) / len(kpis), 2
            )
        }
    
    async def get_weekly_trends(self, telegram_id: int, weeks: int = 4) -> List[Dict[str, Any]]:
        """Get weekly trend data for charts."""
        kpis = await self.get_user_kpis(telegram_id, weeks * 7)
        
        if not kpis:
            return []
        
        # Group by week
        weekly_data = {}
        for kpi in kpis:
            # Get week start date
            timestamp = datetime.fromisoformat(kpi['timestamp'].replace('Z', '+00:00'))
            week_start = timestamp.date() - timedelta(days=timestamp.weekday())
            week_key = week_start.isoformat()
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    'week_start': week_key,
                    'photos': [],
                    'avg_blemish_percent': 0,
                    'min_blemish_percent': float('inf'),
                    'max_blemish_percent': 0
                }
            
            weekly_data[week_key]['photos'].append(kpi)
        
        # Calculate weekly averages
        trends = []
        for week_data in weekly_data.values():
            photos = week_data['photos']
            avg_blemish = sum(p['percent_blemished'] for p in photos) / len(photos)
            min_blemish = min(p['percent_blemished'] for p in photos)
            max_blemish = max(p['percent_blemished'] for p in photos)
            
            trends.append({
                'week_start': week_data['week_start'],
                'photo_count': len(photos),
                'avg_blemish_percent': round(avg_blemish, 2),
                'min_blemish_percent': round(min_blemish, 2),
                'max_blemish_percent': round(max_blemish, 2)
            })
        
        return sorted(trends, key=lambda x: x['week_start'])
    
    def format_progress_message(self, summary: Dict[str, Any]) -> str:
        """Format progress summary into a user-friendly message."""
        if "message" in summary:
            return summary["message"]
        
        blemish = summary["blemish_improvement"]
        photos = summary["total_photos"]
        
        if blemish["improved"]:
            emoji = "✅"
            direction = "improvement"
            change_text = f"decreased by {abs(blemish['change']):.1f}%"
        else:
            emoji = "⚠️"
            direction = "increase"
            change_text = f"increased by {blemish['change']:.1f}%"
        
        return f"""📊 **Skin Progress Report** {emoji}

📸 **Photos analyzed:** {photos}
📅 **Period:** {summary['date_range']['start'][:10]} to {summary['date_range']['end'][:10]}

🎯 **Blemish Progress:**
• Current: {blemish['current_percent']:.1f}%
• Initial: {blemish['initial_percent']:.1f}%
• Change: {change_text}
• Average: {summary['average_blemish_percent']:.1f}%

{emoji} **Overall {direction}** in skin condition detected!
"""

# Example usage functions
async def example_get_user_progress(database, telegram_id: int):
    """Example: Get progress for a user."""
    analyzer = SkinKPIAnalyzer(database)
    
    # Get progress summary
    summary = await analyzer.get_progress_summary(telegram_id)
    message = analyzer.format_progress_message(summary)
    print(message)
    
    # Get weekly trends
    trends = await analyzer.get_weekly_trends(telegram_id)
    for trend in trends:
        print(f"Week {trend['week_start']}: {trend['avg_blemish_percent']:.1f}% avg blemishes ({trend['photo_count']} photos)")

async def example_correlation_analysis(database, telegram_id: int):
    """Example: Correlate skin KPIs with product usage."""
    analyzer = SkinKPIAnalyzer(database)
    
    # Get KPIs and product logs
    kpis = await analyzer.get_user_kpis(telegram_id, 30)
    logs = await database.get_user_logs(telegram_id, 30)
    
    print(f"Found {len(kpis)} photos and {len(logs.get('products', []))} product logs")
    
    # Simple correlation: find photos taken after product usage
    for product_log in logs.get('products', []):
        product_date = datetime.fromisoformat(product_log['logged_at'].replace('Z', '+00:00'))
        
        # Find photos within 3 days after product use
        related_photos = [
            kpi for kpi in kpis 
            if abs((datetime.fromisoformat(kpi['timestamp'].replace('Z', '+00:00')) - product_date).days) <= 3
        ]
        
        if related_photos:
            avg_blemish = sum(p['percent_blemished'] for p in related_photos) / len(related_photos)
            print(f"Product '{product_log['product_name']}' -> {len(related_photos)} photos, {avg_blemish:.1f}% avg blemishes")
