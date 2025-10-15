#!/usr/bin/env python3
"""
Railway Deployment Diagnostics - Check for common startup issues
"""
import os
import sys
import asyncio
import importlib.util
from pathlib import Path

def check_file_structure():
    """Check if all required files exist."""
    print("📁 Checking file structure...")
    
    required_files = {
        'server.py': 'Main server file',
        'bot.py': 'Bot implementation',
        'database.py': 'Database connection',
        'railway.json': 'Railway configuration',
        'requirements-railway.txt': 'Railway dependencies',
        'nixpacks.toml': 'Build configuration'
    }
    
    all_good = True
    for file, description in required_files.items():
        if os.path.exists(file):
            print(f"✅ {file} - {description}")
        else:
            print(f"❌ {file} - {description} (MISSING)")
            all_good = False
    
    return all_good

def check_python_imports():
    """Check if Python can import main modules."""
    print("\n🐍 Checking Python imports...")
    
    modules_to_test = [
        ('fastapi', 'FastAPI framework'),
        ('uvicorn', 'ASGI server'),
        ('telegram', 'python-telegram-bot'),
        ('supabase', 'Supabase client'),
        ('openai', 'OpenAI client'),
        ('PIL', 'Pillow (Image processing)'),
        ('numpy', 'NumPy'),
        ('dotenv', 'python-dotenv')
    ]
    
    import_issues = []
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name} - {description}")
        except ImportError as e:
            print(f"❌ {module_name} - {description} (IMPORT ERROR: {e})")
            import_issues.append(module_name)
    
    return len(import_issues) == 0, import_issues

def check_environment_variables():
    """Check if all required environment variables are available."""
    print("\n🔧 Checking environment variables...")
    
    # Set environment variables from your Railway setup
    test_env = {
        'BASE_URL': 'https://skintracker-production.up.railway.app',
        'TELEGRAM_BOT_TOKEN': '8307648462:AAHrxYiHs965oD_0W0EWUm4Yo3zo3i03YQM',
        'SUPABASE_URL': 'https://vhcbasztxosctnzfyvbu.supabase.co',
        'SUPABASE_ANON_KEY': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        'OPENAI_API_KEY': 'sk-proj-BVaglWbphtXaa8uNEj7rkGlAK2EOE9JYAQlV21OGMrgT4B...',
        'RAILWAY_ENVIRONMENT': 'true',
        'PORT': '8080'
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    required_vars = [
        'BASE_URL',
        'TELEGRAM_BOT_TOKEN', 
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'OPENAI_API_KEY',
        'RAILWAY_ENVIRONMENT',
        'PORT'
    ]
    
    missing_vars = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var}")
        else:
            print(f"❌ {var} (MISSING)")
            missing_vars.append(var)
    
    return len(missing_vars) == 0, missing_vars

async def test_database_connection():
    """Test database connection with your credentials."""
    print("\n🗄️ Testing database connection...")
    
    try:
        from database import Database
        db = Database()
        await db.initialize()
        print("✅ Database connection successful")
        await db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_bot_initialization():
    """Test bot initialization."""
    print("\n🤖 Testing bot initialization...")
    
    try:
        from bot import SkinHealthBot
        bot = SkinHealthBot()
        print("✅ Bot object created")
        
        # Test initialization (but don't actually start)
        await bot.initialize()
        print("✅ Bot initialization successful")
        
        await bot.shutdown()
        print("✅ Bot shutdown successful")
        return True
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")
        import traceback
        print(f"   Full error: {traceback.format_exc()}")
        return False

def test_server_import():
    """Test if server.py can be imported."""
    print("\n🌐 Testing server import...")
    
    try:
        import server
        print("✅ Server module imported successfully")
        
        # Check if FastAPI app exists
        if hasattr(server, 'app'):
            print("✅ FastAPI app object found")
            return True
        else:
            print("❌ FastAPI app object not found")
            return False
    except Exception as e:
        print(f"❌ Server import failed: {e}")
        import traceback
        print(f"   Full error: {traceback.format_exc()}")
        return False

def check_railway_configuration():
    """Check Railway-specific configuration."""
    print("\n🚄 Checking Railway configuration...")
    
    # Check railway.json
    try:
        import json
        with open('railway.json', 'r') as f:
            config = json.load(f)
        
        print(f"✅ railway.json loaded")
        print(f"   Start command: {config.get('deploy', {}).get('startCommand', 'Not set')}")
        print(f"   Health check: {config.get('deploy', {}).get('healthcheckPath', 'Not set')}")
        
        return True
    except Exception as e:
        print(f"❌ railway.json issue: {e}")
        return False

async def run_full_diagnostic():
    """Run all diagnostic tests."""
    print("🔍 Railway Deployment Diagnostic Tool")
    print("=" * 50)
    
    tests = [
        ("File Structure", check_file_structure),
        ("Python Imports", check_python_imports),
        ("Environment Variables", check_environment_variables),
        ("Railway Configuration", check_railway_configuration),
        ("Server Import", test_server_import),
        ("Database Connection", test_database_connection),
        ("Bot Initialization", test_bot_initialization)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            # Handle functions that return tuples (result, details)
            if isinstance(result, tuple):
                results[test_name] = result[0]
                if not result[0] and len(result) > 1:
                    print(f"   Issues: {result[1]}")
            else:
                results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Diagnostic Summary")
    print("=" * 50)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    # Recommendations
    if passed < total:
        print("\n🔧 Likely Issues:")
        
        if not results.get("Python Imports"):
            print("  • Missing Python dependencies")
            print("    → Check requirements-railway.txt")
            print("    → Verify nixpacks.toml build process")
        
        if not results.get("Database Connection"):
            print("  • Database connection problems")
            print("    → Verify Supabase credentials")
            print("    → Check network connectivity from Railway")
        
        if not results.get("Bot Initialization"):
            print("  • Bot initialization issues")
            print("    → Check Telegram bot token")
            print("    → Verify bot permissions")
        
        if not results.get("Server Import"):
            print("  • Server startup problems")
            print("    → Check server.py for syntax errors")
            print("    → Verify all imports work")
        
        print(f"\n💡 Next Steps:")
        print(f"  1. Fix the failed tests above")
        print(f"  2. Check Railway deployment logs")
        print(f"  3. Test locally: python server.py")
        print(f"  4. Redeploy on Railway")
    else:
        print("\n✅ All tests passed! Railway should be working.")
        print("   If still getting 502, check Railway logs for runtime errors.")

if __name__ == "__main__":
    asyncio.run(run_full_diagnostic())
