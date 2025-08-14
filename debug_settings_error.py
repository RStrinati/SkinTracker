#!/usr/bin/env python3

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

async def debug_settings_error():
    """Debug the specific settings error"""
    try:
        from database import Database
        from dotenv import load_dotenv
        
        load_dotenv()
        
        print("=== Debugging Settings Error ===")
        
        # Test database methods
        database = Database()
        test_telegram_id = 6865543260
        
        print("1. Testing get_user_by_telegram_id...")
        user = await database.get_user_by_telegram_id(test_telegram_id)
        if user:
            print(f"   ✅ User found: {user.get('id', 'No ID')}")
            print(f"   📧 Reminder time: {user.get('reminder_time', 'Not set')}")
        else:
            print("   ❌ User not found")
            return
        
        print("2. Testing get_conditions...")
        conditions = await database.get_conditions(test_telegram_id)
        print(f"   📋 Found {len(conditions)} conditions")
        
        print("3. Testing get_products...")
        products = await database.get_products(test_telegram_id)
        print(f"   🧴 Found {len(products)} products")
        
        print("✅ All database methods working correctly")
        
        # The issue might be in the settings method itself
        print("\n🔧 Potential issues to check:")
        print("   • Make sure daily_mood_logs table exists (run migration)")
        print("   • Check if there are any syntax errors in _show_settings")
        print("   • Restart the server after code changes")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_settings_error())
