#!/usr/bin/env python3
"""
Simple test to check if server.py can start without actually running the server
"""
import os
import sys

# Set minimal environment variables
os.environ['RAILWAY_ENVIRONMENT'] = 'true'
os.environ['PORT'] = '8080'

print("🔍 Testing server.py startup issues...")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

# Test 1: Can we import the main modules?
print("\n📦 Testing imports...")
try:
    import fastapi
    print("✅ FastAPI imported")
except Exception as e:
    print(f"❌ FastAPI failed: {e}")
    sys.exit(1)

try:
    import uvicorn
    print("✅ Uvicorn imported")
except Exception as e:
    print(f"❌ Uvicorn failed: {e}")
    sys.exit(1)

# Test 2: Can we import our modules?
print("\n🔧 Testing application modules...")
try:
    import database
    print("✅ Database module imported")
except Exception as e:
    print(f"❌ Database module failed: {e}")
    print("This could be the issue!")

try:
    import bot
    print("✅ Bot module imported")
except Exception as e:
    print(f"❌ Bot module failed: {e}")
    print("This could be the issue!")

# Test 3: Can we import server.py?
print("\n🌐 Testing server module...")
try:
    import server
    print("✅ Server module imported")
    
    if hasattr(server, 'app'):
        print("✅ FastAPI app found")
    else:
        print("❌ No FastAPI app found in server module")
        
except Exception as e:
    print(f"❌ Server module failed: {e}")
    print("This is likely the root cause!")
    import traceback
    print("\nFull error:")
    traceback.print_exc()

print("\n🎯 Test completed!")
print("If server module failed to import, that's why Railway can't start the app.")
