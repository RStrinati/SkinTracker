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

async def debug_scheduler():
    """Debug the scheduler to understand what's happening"""
    load_dotenv()
    bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
    scheduler = ReminderScheduler(bot)
    
    print("=== Scheduler Debug ===")
    print(f"Current time: {datetime.now()}")
    print(f"Scheduler type: {type(scheduler.scheduler)}")
    print(f"Scheduler module: {scheduler.scheduler.__class__.__module__}")
    
    # Check available methods/attributes
    available_attrs = [attr for attr in dir(scheduler.scheduler) if not attr.startswith('_')]
    print(f"Available scheduler attributes: {available_attrs}")
    
    # Try to get jobs using different methods
    try:
        # Try the jobs attribute
        if hasattr(scheduler.scheduler, 'jobs'):
            jobs = scheduler.scheduler.jobs
            print(f"Jobs (via .jobs): {jobs}")
        
        # Try get_jobs method
        if hasattr(scheduler.scheduler, 'get_jobs'):
            jobs = scheduler.scheduler.get_jobs()
            print(f"Jobs (via .get_jobs()): {list(jobs)}")
            
        # Check if we can get a specific job
        job = scheduler.scheduler.get_job("reminder_6865543260")
        print(f"Specific job for user 6865543260: {job}")
        
    except Exception as e:
        print(f"Error accessing jobs: {e}")
    
    # Test manual reminder
    print("\n=== Testing Manual Reminder ===")
    try:
        await scheduler.send_daily_reminder(6865543260)
        print("✅ Manual reminder sent successfully!")
    except Exception as e:
        print(f"❌ Manual reminder failed: {e}")
    
    # Test scheduling a new reminder for 2 minutes from now
    print("\n=== Testing Scheduling ===")
    try:
        future_time = datetime.now() + timedelta(minutes=2)
        time_str = future_time.strftime('%H:%M')
        print(f"Scheduling reminder for {time_str} (2 minutes from now)")
        
        scheduler.schedule_daily_reminder(6865543260, time_str)
        print("✅ Reminder scheduled successfully!")
        
        # Check if job was actually created
        job = scheduler.scheduler.get_job("reminder_6865543260")
        if job:
            print(f"✅ Job found: {job}")
            if hasattr(job, 'next_run_time'):
                print(f"   Next run time: {job.next_run_time}")
        else:
            print("❌ Job not found after scheduling!")
            
    except Exception as e:
        print(f"❌ Scheduling failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_scheduler())
