#!/usr/bin/env python3

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

from reminder_scheduler import ReminderScheduler
from telegram import Bot
from dotenv import load_dotenv

async def test_live_reminder():
    """Test that a scheduled reminder actually gets delivered"""
    load_dotenv()
    bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
    scheduler = ReminderScheduler(bot)
    
    print("=== Live Reminder Test ===")
    current_time = datetime.now()
    print(f"Current time: {current_time}")
    
    # Schedule a reminder for 1 minute from now
    future_time = current_time + timedelta(minutes=1)
    time_str = future_time.strftime('%H:%M')
    
    print(f"Scheduling reminder for {time_str} (1 minute from now)")
    scheduler.schedule_daily_reminder(6865543260, time_str)
    
    # Verify the job was created
    job = scheduler.scheduler.get_job("reminder_6865543260")
    if job:
        print(f"✅ Job scheduled successfully!")
        print(f"   Next run time: {job.next_run_time}")
        
        # Wait for the reminder to be sent
        wait_seconds = 65  # Wait a bit longer than 1 minute
        print(f"⏳ Waiting {wait_seconds} seconds for the reminder to be sent...")
        print(f"   Check your Telegram at approximately {future_time.strftime('%H:%M:%S')}")
        
        # Keep the event loop running so the scheduler can execute
        await asyncio.sleep(wait_seconds)
        
        print("✅ Test completed! Check if you received the reminder message.")
        
    else:
        print("❌ Failed to schedule the job!")
    
    # Cleanup
    scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(test_live_reminder())
