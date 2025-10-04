"""
Railway deployment fix script
This script helps diagnose and fix common Railway deployment issues
"""
import os
import json
from pathlib import Path

def check_and_fix_environment():
    """Check and suggest fixes for environment variables."""
    print("🔧 Railway Environment Configuration")
    print("=" * 50)
    
    # Required environment variables
    required_vars = {
        'TELEGRAM_BOT_TOKEN': 'Your Telegram bot token from @BotFather',
        'SUPABASE_URL': 'Your Supabase project URL (e.g., https://xxxxx.supabase.co)',
        'SUPABASE_ANON_KEY': 'Your Supabase anon public key',
        'SUPABASE_SERVICE_ROLE_KEY': 'Your Supabase service role key (for admin operations)',
        'OPENAI_API_KEY': 'Your OpenAI API key',
        'BASE_URL': 'Your Railway deployment URL (e.g., https://skintracker-production.up.railway.app)',
        'PORT': '8080 (Railway default)',
        'RAILWAY_ENVIRONMENT': 'production'
    }
    
    print("Required environment variables for Railway:")
    print()
    
    for var, description in required_vars.items():
        current_value = os.getenv(var)
        if current_value:
            print(f"✅ {var}: Set ({'*' * 10}...{current_value[-4:]})")
        else:
            print(f"❌ {var}: Missing")
            print(f"   Description: {description}")
            print()
    
    # Generate Railway CLI commands
    print("\n🚀 Railway CLI Commands to Set Missing Variables:")
    print("=" * 50)
    
    missing_vars = [var for var in required_vars.keys() if not os.getenv(var)]
    
    if missing_vars:
        print("Run these commands in your Railway project directory:")
        print()
        for var in missing_vars:
            print(f"railway variables set {var}=YOUR_VALUE_HERE")
        
        print("\nOr set them in the Railway dashboard:")
        print("1. Go to https://railway.app/dashboard")
        print("2. Select your SkinTracker project")
        print("3. Go to Variables tab")
        print("4. Add the missing variables")
    else:
        print("✅ All environment variables are set!")

def create_railway_deployment_checklist():
    """Create a deployment checklist."""
    print("\n📋 Railway Deployment Checklist")
    print("=" * 50)
    
    checklist = [
        "✅ Environment variables set in Railway dashboard",
        "✅ Supabase project created and configured",
        "✅ Telegram bot created with @BotFather",
        "✅ OpenAI API key obtained",
        "✅ Railway project connected to GitHub repository",
        "✅ requirements-railway.txt contains all needed dependencies",
        "✅ nixpacks.toml configured properly",
        "✅ Webhook URL set correctly with Telegram"
    ]
    
    for item in checklist:
        print(f"  {item}")
    
    print("\n🔍 Debugging Steps:")
    print("1. Check Railway deployment logs: `railway logs`")
    print("2. Test health endpoint: `curl https://your-app.up.railway.app/health`")
    print("3. Verify webhook: Test with Telegram bot")
    print("4. Check database connection: Verify Supabase credentials")

def fix_potential_issues():
    """Fix common deployment issues."""
    print("\n🔧 Applying Fixes")
    print("=" * 50)
    
    # Check and fix railway.json
    railway_config = {
        "$schema": "https://railway.app/railway.schema.json",
        "build": {
            "builder": "NIXPACKS"
        },
        "deploy": {
            "startCommand": "python server.py",
            "healthcheckPath": "/health",
            "healthcheckTimeout": 300,
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 5
        }
    }
    
    # Ensure railway.json is correct
    if Path('railway.json').exists():
        with open('railway.json', 'r') as f:
            current_config = json.load(f)
        
        if current_config == railway_config:
            print("✅ railway.json is correctly configured")
        else:
            print("⚠️ railway.json needs updating")
            with open('railway.json', 'w') as f:
                json.dump(railway_config, f, indent=2)
            print("✅ Updated railway.json")
    else:
        with open('railway.json', 'w') as f:
            json.dump(railway_config, f, indent=2)
        print("✅ Created railway.json")
    
    # Check Procfile
    procfile_content = "web: python server.py\n"
    if Path('Procfile').exists():
        with open('Procfile', 'r') as f:
            current_procfile = f.read()
        
        if current_procfile.strip() == procfile_content.strip():
            print("✅ Procfile is correctly configured")
        else:
            print("⚠️ Procfile needs updating")
            with open('Procfile', 'w') as f:
                f.write(procfile_content)
            print("✅ Updated Procfile")
    else:
        with open('Procfile', 'w') as f:
            f.write(procfile_content)
        print("✅ Created Procfile")

def generate_webhook_setup_commands():
    """Generate commands to set up the webhook."""
    print("\n🌐 Webhook Setup Commands")
    print("=" * 50)
    
    base_url = os.getenv('BASE_URL', 'https://your-app.up.railway.app')
    
    print("After your Railway deployment is working, run these commands:")
    print()
    print("1. Set the webhook URL:")
    print(f"   curl -X POST 'https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook' \\")
    print(f"        -d 'url={base_url}/api/v1/webhook'")
    print()
    print("2. Verify webhook is set:")
    print("   curl 'https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo'")
    print()
    print("3. Test the webhook endpoint:")
    print(f"   curl {base_url}/api/v1/webhook")

def check_callback_handling():
    """Check if callback handling is working properly."""
    print("\n🔄 Callback Handling Analysis")
    print("=" * 50)
    
    try:
        with open('bot.py', 'r', encoding='utf-8') as f:
            bot_content = f.read()
        
        # Check for essential callback patterns
        callback_patterns = [
            ('rating_ callbacks', 'rating_' in bot_content),
            ('log_daily_mood function', 'log_daily_mood' in bot_content),
            ('handle_callback function', 'handle_callback' in bot_content),
            ('callback query handling', 'callback_query' in bot_content.lower()),
            ('reminder scheduler', 'ReminderScheduler' in bot_content)
        ]
        
        print("Callback handling components:")
        all_present = True
        for pattern_name, present in callback_patterns:
            status = "✅" if present else "❌"
            print(f"  {status} {pattern_name}")
            if not present:
                all_present = False
        
        if all_present:
            print("\n✅ All callback handling components are present")
            print("Issue is likely with deployment or webhook setup")
        else:
            print("\n❌ Some callback handling components are missing")
            print("This could explain why responses aren't being registered")
            
    except Exception as e:
        print(f"❌ Error checking bot.py: {e}")

def main():
    """Run all diagnostic and fix procedures."""
    print("🚀 Railway Deployment Fix & Diagnostic Tool")
    print("=" * 60)
    
    check_and_fix_environment()
    create_railway_deployment_checklist()
    fix_potential_issues()
    check_callback_handling()
    generate_webhook_setup_commands()
    
    print("\n" + "=" * 60)
    print("🎯 Next Steps:")
    print("1. Set missing environment variables in Railway dashboard")
    print("2. Redeploy your Railway application")
    print("3. Test the health endpoint")
    print("4. Set up the webhook with Telegram")
    print("5. Test the reminder functionality")
    print("\n💡 If issues persist, check Railway logs with: railway logs")

if __name__ == "__main__":
    main()
