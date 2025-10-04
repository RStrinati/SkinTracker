#!/usr/bin/env python3
"""
Environment Variable Configuration Guide for Railway SkinTracker Deployment
"""

def show_required_variables():
    print("🔧 Required Environment Variables for Railway SkinTracker")
    print("=" * 60)
    print()
    
    variables = [
        {
            "name": "TELEGRAM_BOT_TOKEN",
            "description": "Your Telegram bot token from BotFather",
            "format": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
            "required": True,
            "source": "Get from @BotFather on Telegram"
        },
        {
            "name": "SUPABASE_URL",
            "description": "Your Supabase project URL",
            "format": "https://abcdefghijklmnop.supabase.co",
            "required": True,
            "source": "Supabase Dashboard > Settings > API"
        },
        {
            "name": "SUPABASE_ANON_KEY",
            "description": "Your Supabase anonymous public key",
            "format": "eyJ0eXAiOiJKV1QiLCJhbGciOiJI...",
            "required": True,
            "source": "Supabase Dashboard > Settings > API"
        },
        {
            "name": "BASE_URL",
            "description": "Your Railway deployment URL",
            "format": "https://skintracker-production.up.railway.app",
            "required": True,
            "source": "Railway Dashboard > Your Service > Settings"
        },
        {
            "name": "PORT",
            "description": "Port for the application (Railway default)",
            "format": "8080",
            "required": False,
            "source": "Usually auto-set by Railway"
        },
        {
            "name": "HOST",
            "description": "Host binding for the application",
            "format": "0.0.0.0",
            "required": False,
            "source": "Should be 0.0.0.0 for Railway"
        }
    ]
    
    for i, var in enumerate(variables, 1):
        status = "🔴 REQUIRED" if var["required"] else "🟡 OPTIONAL"
        print(f"{i}. {var['name']} {status}")
        print(f"   📝 Description: {var['description']}")
        print(f"   📋 Format: {var['format']}")
        print(f"   📍 Source: {var['source']}")
        print()
    
    print("🚨 Common Issues and Solutions:")
    print("-" * 30)
    print("❌ TELEGRAM_BOT_TOKEN invalid format")
    print("   ➤ Should start with numbers, then colon, then letters/numbers")
    print("   ➤ Example: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    print()
    print("❌ SUPABASE_URL wrong format")
    print("   ➤ Should start with https:// and end with .supabase.co")
    print("   ➤ Example: https://abcdefghijklmnop.supabase.co")
    print()
    print("❌ SUPABASE_ANON_KEY not the right key")
    print("   ➤ Use the 'anon public' key, NOT the service_role key")
    print("   ➤ Should start with 'eyJ0eXAiOiJKV1QiLCJhbGciOiJI'")
    print()
    print("❌ BASE_URL incorrect")
    print("   ➤ Should be your Railway service URL")
    print("   ➤ Example: https://skintracker-production.up.railway.app")
    print()
    
    print("🔄 After Setting Variables:")
    print("-" * 25)
    print("1. Railway should automatically redeploy")
    print("2. Wait 2-3 minutes for deployment to complete")
    print("3. Check deployment logs in Railway dashboard")
    print("4. Test endpoints again")
    print()
    
    print("🔍 Debugging Steps:")
    print("-" * 18)
    print("1. Go to Railway Dashboard > Your Project > Variables")
    print("2. Verify all required variables are set")
    print("3. Check Railway Dashboard > Deployments for status")
    print("4. View logs in Railway Dashboard > View Logs")
    print("5. Look for error messages during startup")

def check_railway_deployment_status():
    print("\n📡 Quick Railway Status Check:")
    print("-" * 30)
    
    import requests
    try:
        response = requests.get("https://skintracker-production.up.railway.app/health", timeout=10)
        if response.status_code == 200:
            print("✅ Deployment is WORKING!")
            return True
        elif response.status_code == 502:
            print("❌ Still getting 502 - deployment may be in progress or failed")
            return False
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - deployment may be starting")
        return False
    except requests.exceptions.ConnectionError:
        print("🔌 Connection failed - deployment may be in progress")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    show_required_variables()
    
    # Quick status check
    is_working = check_railway_deployment_status()
    
    if not is_working:
        print("\n💡 Troubleshooting Tips:")
        print("=" * 25)
        print("• Double-check all environment variables in Railway")
        print("• Ensure no extra spaces or quotes around values")
        print("• Wait a few minutes after setting variables")
        print("• Check Railway logs for specific error messages")
        print("• Try manually redeploying from Railway dashboard")
