#!/usr/bin/env python3

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

from database import Database
from dotenv import load_dotenv

async def test_mood_logging():
    """Test the daily mood logging functionality"""
    load_dotenv()
    
    print("=== Testing Daily Mood Logging ===")
    
    # Initialize database
    db = Database()
    
    test_telegram_id = 6865543260  # Your telegram ID
    
    # Test logging different moods
    moods_to_test = [
        (5, "Excellent"),
        (4, "Good"),
        (3, "Okay"),
        (2, "Bad"),
        (1, "Flare-up")
    ]
    
    print("\n1. Testing mood logging:")
    for rating, description in moods_to_test:
        success = await db.log_daily_mood(test_telegram_id, rating, description)
        status = "✅" if success else "❌"
        print(f"   {status} Logged: {description} ({rating}/5)")
    
    print("\n2. Testing mood retrieval:")
    recent_moods = await db.get_recent_mood_logs(test_telegram_id, days=7)
    print(f"   Found {len(recent_moods)} recent mood logs")
    
    for mood in recent_moods[:3]:  # Show first 3
        print(f"   • {mood['logged_at'][:10]}: {mood['mood_description']} ({mood['mood_rating']}/5)")
    
    print("\n3. Testing mood statistics:")
    mood_stats = await db.get_mood_stats(test_telegram_id, days=30)
    print(f"   Total entries: {mood_stats.get('total_entries', 0)}")
    print(f"   Average rating: {mood_stats.get('average_rating', 0)}")
    print(f"   Trend: {mood_stats.get('trend', 'Unknown')}")
    
    mood_dist = mood_stats.get('mood_distribution', {})
    if mood_dist:
        print("   Mood distribution:")
        for mood, count in mood_dist.items():
            print(f"     • {mood}: {count}")
    
    print("\n✅ Mood logging test completed!")
    print("\nNow you can:")
    print("1. Execute the daily_mood_migration.sql in Supabase dashboard")
    print("2. Restart your bot server")
    print("3. Test a reminder - when you click a mood button, it will be logged!")

if __name__ == "__main__":
    asyncio.run(test_mood_logging())
