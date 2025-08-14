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

async def test_scheduler_status():
    """Test the current status of the reminder scheduler"""
    load_dotenv()
    bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
    scheduler = ReminderScheduler(bot)
    
    print("=== Reminder Scheduler Status ===")
    print(f"Current time: {datetime.now()}")
    
    # Check if scheduler is running
    print(f"Scheduler running: {scheduler.scheduler.running}")
    
    # Get all jobs (correctly using the property)
    jobs = list(scheduler.scheduler.get_jobs())
    print(f"Number of active jobs: {len(jobs)}")
    
    if jobs:
        for job in jobs:
            print(f"Job ID: {job.id}")
            print(f"  Next run: {job.next_run_time}")
            print(f"  Function: {job.func}")
            print(f"  Args: {job.args}")
            print()
    else:
        print("No active jobs found!")
        
        # Try to schedule a test reminder for 1 minute from now
        test_time = datetime.now() + timedelta(minutes=1)
        print(f"Scheduling test reminder for {test_time.strftime('%H:%M:%S')}")
        
        await scheduler.schedule_daily_reminder(6865543260, test_time.strftime('%H:%M'))
        
        # Check jobs again
        jobs = list(scheduler.scheduler.get_jobs())
        print(f"Jobs after scheduling: {len(jobs)}")
        
        if jobs:
            for job in jobs:
                print(f"New Job ID: {job.id}")
                print(f"  Next run: {job.next_run_time}")

if __name__ == "__main__":
    asyncio.run(test_scheduler_status())
