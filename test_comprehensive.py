#!/usr/bin/env python3
"""
Comprehensive test script for SkinTracker codebase.
Tests all major functionality and identifies issues.
"""

import asyncio
import sys
import os
from pathlib import Path
import requests
import json
import traceback

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from database import Database
from dotenv import load_dotenv

load_dotenv()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test(name, passed, details=""):
    """Print test result with color coding."""
    status = f"{Colors.GREEN}✓ PASS{Colors.ENDC}" if passed else f"{Colors.RED}✗ FAIL{Colors.ENDC}"
    print(f"{status} {name}")
    if details:
        print(f"     {details}")

async def test_database_connection():
    """Test database connectivity and basic operations."""
    try:
        db = Database()
        await db.initialize()
        
        # Test basic query
        result = db.client.table('users').select('id').limit(1).execute()
        return True, f"Database connected, {len(result.data)} users found"
    except Exception as e:
        return False, f"Database error: {str(e)}"

async def test_timeline_api():
    """Test timeline API endpoints."""
    base_url = "http://localhost:8081"
    test_user = 6865543260
    
    tests = []
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        tests.append(("Health endpoint", response.status_code == 200, f"Status: {response.status_code}"))
    except Exception as e:
        tests.append(("Health endpoint", False, f"Error: {str(e)}"))
    
    # Test timeline events
    try:
        response = requests.get(f"{base_url}/api/v1/timeline/events?telegram_id={test_user}&limit=5", timeout=10)
        if response.status_code == 200:
            data = response.json()
            tests.append(("Timeline events", True, f"Found {data.get('total_count', 0)} events"))
        else:
            tests.append(("Timeline events", False, f"Status: {response.status_code}"))
    except Exception as e:
        tests.append(("Timeline events", False, f"Error: {str(e)}"))
    
    # Test trigger insights
    try:
        response = requests.get(f"{base_url}/api/v1/timeline/insights/triggers?telegram_id={test_user}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            tests.append(("Trigger insights", True, f"Found {len(data)} insights"))
        else:
            tests.append(("Trigger insights", False, f"Status: {response.status_code}"))
    except Exception as e:
        tests.append(("Trigger insights", False, f"Error: {str(e)}"))
    
    # Test product insights
    try:
        response = requests.get(f"{base_url}/api/v1/timeline/insights/products?telegram_id={test_user}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            tests.append(("Product insights", True, f"Found {len(data)} insights"))
        else:
            tests.append(("Product insights", False, f"Status: {response.status_code}"))
    except Exception as e:
        tests.append(("Product insights", False, f"Error: {str(e)}"))
    
    # Test timeline page
    try:
        response = requests.get(f"{base_url}/timeline", timeout=5)
        tests.append(("Timeline page", response.status_code == 200, f"Status: {response.status_code}"))
    except Exception as e:
        tests.append(("Timeline page", False, f"Error: {str(e)}"))
    
    return tests

def test_file_structure():
    """Test that all required files exist."""
    required_files = [
        "bot.py",
        "server.py", 
        "database.py",
        "api/timeline.py",
        "api/__init__.py",
        "components/SkinTimeline.tsx",
        "public/timeline.html",
        ".env",
        "requirements.txt",
        "package.json"
    ]
    
    tests = []
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        exists = full_path.exists()
        tests.append((f"File: {file_path}", exists, f"Path: {full_path}"))
    
    return tests

def test_environment_variables():
    """Test that required environment variables are set."""
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "NEXT_PUBLIC_SUPABASE_URL", 
        "SUPABASE_SERVICE_ROLE_KEY",
        "OPENAI_API_KEY"
    ]
    
    tests = []
    for var in required_vars:
        value = os.getenv(var)
        has_value = value is not None and len(value) > 0
        masked_value = f"{value[:10]}..." if has_value else "None"
        tests.append((f"Env var: {var}", has_value, f"Value: {masked_value}"))
    
    return tests

async def test_bot_imports():
    """Test that all bot-related modules can be imported."""
    modules_to_test = [
        "bot",
        "server", 
        "database",
        "openai_service",
        "reminder_scheduler",
        "skin_analysis"
    ]
    
    tests = []
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            tests.append((f"Import: {module_name}", True, ""))
        except Exception as e:
            tests.append((f"Import: {module_name}", False, f"Error: {str(e)}"))
    
    return tests

async def main():
    """Run comprehensive test suite."""
    print(f"{Colors.BOLD}{Colors.BLUE}🧪 SkinTracker Comprehensive Test Suite{Colors.ENDC}")
    print("=" * 50)
    
    all_tests = []
    
    # Test 1: File Structure
    print(f"\n{Colors.BOLD}📁 File Structure Tests{Colors.ENDC}")
    file_tests = test_file_structure()
    for test_name, passed, details in file_tests:
        print_test(test_name, passed, details)
    all_tests.extend(file_tests)
    
    # Test 2: Environment Variables
    print(f"\n{Colors.BOLD}🔧 Environment Variables{Colors.ENDC}")
    env_tests = test_environment_variables()
    for test_name, passed, details in env_tests:
        print_test(test_name, passed, details)
    all_tests.extend(env_tests)
    
    # Test 3: Module Imports
    print(f"\n{Colors.BOLD}📦 Module Import Tests{Colors.ENDC}")
    import_tests = await test_bot_imports()
    for test_name, passed, details in import_tests:
        print_test(test_name, passed, details)
    all_tests.extend(import_tests)
    
    # Test 4: Database Connection
    print(f"\n{Colors.BOLD}🗄️  Database Tests{Colors.ENDC}")
    try:
        db_passed, db_details = await test_database_connection()
        print_test("Database connection", db_passed, db_details)
        all_tests.append(("Database connection", db_passed, db_details))
    except Exception as e:
        print_test("Database connection", False, f"Exception: {str(e)}")
        all_tests.append(("Database connection", False, f"Exception: {str(e)}"))
    
    # Test 5: API Endpoints
    print(f"\n{Colors.BOLD}🌐 API Endpoint Tests{Colors.ENDC}")
    try:
        api_tests = await test_timeline_api()
        for test_name, passed, details in api_tests:
            print_test(test_name, passed, details)
        all_tests.extend(api_tests)
    except Exception as e:
        print_test("API tests", False, f"Exception: {str(e)}")
        all_tests.append(("API tests", False, f"Exception: {str(e)}"))
    
    # Summary
    print(f"\n{Colors.BOLD}📊 Test Summary{Colors.ENDC}")
    print("=" * 50)
    
    passed_tests = [t for t in all_tests if t[1]]
    failed_tests = [t for t in all_tests if not t[1]]
    
    print(f"Total tests: {len(all_tests)}")
    print(f"{Colors.GREEN}Passed: {len(passed_tests)}{Colors.ENDC}")
    print(f"{Colors.RED}Failed: {len(failed_tests)}{Colors.ENDC}")
    
    if failed_tests:
        print(f"\n{Colors.RED}❌ Failed Tests:{Colors.ENDC}")
        for test_name, _, details in failed_tests:
            print(f"  • {test_name}: {details}")
    
    if len(passed_tests) == len(all_tests):
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All tests passed! System is healthy.{Colors.ENDC}")
    else:
        success_rate = (len(passed_tests) / len(all_tests)) * 100
        print(f"\n{Colors.YELLOW}⚠️  System health: {success_rate:.1f}% ({len(passed_tests)}/{len(all_tests)} tests passed){Colors.ENDC}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Test suite error: {str(e)}{Colors.ENDC}")
        traceback.print_exc()
