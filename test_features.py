#!/usr/bin/env python3
"""Test script for new UX features"""

import asyncio
import sys
from database import Database

async def test_new_features():
    """Test the new database methods and features"""
    try:
        print("🧪 Testing Enhanced UX Features...")
        
        db = Database()
        await db.initialize()
        print("✅ Database connection established")
        
        # Test 1: Today's logs
        print("\n📅 Testing get_today_logs...")
        today_logs = await db.get_today_logs(6865543260)
        print(f"Today logs: {today_logs}")
        
        # Test 2: User areas
        print("\n🎯 Testing get_user_areas...")
        areas = await db.get_user_areas(6865543260)
        print(f"User areas: {areas}")
        
        # Test 3: Create a test area with unique name
        print("\n➕ Testing create_user_area...")
        import time
        unique_area_name = f"Test Area {int(time.time())}"
        success = await db.create_user_area(6865543260, unique_area_name, "Test description")
        print(f"Area creation success: {success}")
        
        # Test 4: Check areas again
        print("\n🔄 Re-checking user areas...")
        areas_after = await db.get_user_areas(6865543260)
        print(f"User areas after creation: {areas_after}")
        
        # Test 5: Test onboarding status
        print("\n🚀 Testing update_user_onboarding_status...")
        onboard_success = await db.update_user_onboarding_status(6865543260, True)
        print(f"Onboarding update success: {onboard_success}")
        
        await db.close()
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_new_features())
