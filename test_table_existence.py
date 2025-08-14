#!/usr/bin/env python3

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

from database import Database
from dotenv import load_dotenv

async def test_table_existence():
    """Test if daily_mood_logs table exists"""
    load_dotenv()
    
    print("=== Testing Table Existence ===")
    
    # Initialize database
    db = Database()
    
    # Test if daily_mood_logs table exists
    try:
        # Try to query the table - if it doesn't exist, this will fail
        result = db.client.table('daily_mood_logs').select('id').limit(1).execute()
        print("✅ daily_mood_logs table EXISTS")
        print(f"   Response: {len(result.data)} rows found")
        return True
    except Exception as e:
        print("❌ daily_mood_logs table DOES NOT EXIST")
        print(f"   Error: {e}")
        return False

async def test_all_tables():
    """Test which tables exist"""
    load_dotenv()
    db = Database()
    
    tables_to_test = [
        'users',
        'products', 
        'product_logs',
        'triggers',
        'trigger_logs',
        'symptom_logs',
        'photo_logs',
        'conditions',
        'skin_kpis',
        'daily_mood_logs'  # This is the new one
    ]
    
    print("\n📊 Table Existence Check:")
    existing_tables = []
    missing_tables = []
    
    for table in tables_to_test:
        try:
            result = db.client.table(table).select('id').limit(1).execute()
            print(f"   ✅ {table}")
            existing_tables.append(table)
        except Exception as e:
            print(f"   ❌ {table} - {str(e)[:50]}...")
            missing_tables.append(table)
    
    print(f"\n📈 Summary:")
    print(f"   Existing: {len(existing_tables)}")
    print(f"   Missing: {len(missing_tables)}")
    
    if missing_tables:
        print(f"\n🔧 Missing tables: {', '.join(missing_tables)}")
        print("   You need to run the migration SQL scripts!")

if __name__ == "__main__":
    asyncio.run(test_all_tables())
