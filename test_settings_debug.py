#!/usr/bin/env python3

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

async def test_settings_method():
    """Test the settings method directly to find the error"""
    try:
        from bot import SkinHealthBot
        from database import Database
        from dotenv import load_dotenv
        
        load_dotenv()
        
        print("=== Testing Settings Method ===")
        
        # Initialize bot components
        database = Database()
        bot = SkinHealthBot(database)
        
        print("✅ Bot initialized successfully")
        
        # Create a mock update object
        class MockUser:
            def __init__(self):
                self.id = 6865543260
        
        class MockMessage:
            def __init__(self):
                pass
                
            async def reply_text(self, text, parse_mode=None, reply_markup=None):
                print(f"📱 Bot would send: {text}")
                return True
        
        class MockUpdate:
            def __init__(self):
                self.effective_user = MockUser()
                self.message = MockMessage()
                self.callback_query = None
        
        # Test the settings method
        update = MockUpdate()
        context = {}
        
        print("🔧 Testing _show_settings method...")
        await bot._show_settings(update, context)
        print("✅ Settings method completed successfully")
        
    except Exception as e:
        print(f"❌ Error in settings method: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_settings_method())
