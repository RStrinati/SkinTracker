#!/usr/bin/env python3
"""
Script to verify and fix Railway deployment issues
"""
import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

async def get_railway_webhook_info():
    """Get current webhook info from Telegram."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found")
        return None
    
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                webhook_info = data.get('result', {})
                return webhook_info
            else:
                print(f"❌ Failed to get webhook info: {response.status_code}")
                return None
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")
        return None

async def set_railway_webhook(railway_url):
    """Set webhook to Railway URL."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found")
        return False
    
    webhook_url = f"{railway_url}/api/v1/webhook"
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"url": webhook_url})
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    print(f"✅ Webhook set successfully to: {webhook_url}")
                    return True
                else:
                    print(f"❌ Failed to set webhook: {data}")
                    return False
            else:
                print(f"❌ HTTP error setting webhook: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False

async def test_railway_endpoint(railway_url):
    """Test Railway deployment health."""
    health_url = f"{railway_url}/health"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(health_url, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Railway deployment is healthy")
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   Environment: {data.get('services', {}).get('environment', 'unknown')}")
                return True
            else:
                print(f"❌ Railway health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Error testing Railway endpoint: {e}")
        return False

def generate_railway_fix_commands(railway_url):
    """Generate commands to fix Railway deployment."""
    print("\n" + "="*60)
    print("🔧 RAILWAY DEPLOYMENT FIX STEPS")
    print("="*60)
    
    print("\n1. SET ENVIRONMENT VARIABLES in Railway Dashboard:")
    print(f"   BASE_URL = {railway_url}")
    print(f"   RAILWAY_ENVIRONMENT = true")
    print(f"   PORT = 8080")
    
    print("\n2. UPDATE WEBHOOK (run this after setting env vars):")
    print(f"   curl -X POST '{railway_url}/api/v1/set-webhook'")
    
    print("\n3. VERIFY WEBHOOK (check current setting):")
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN')
    print(f"   curl 'https://api.telegram.org/bot{bot_token}/getWebhookInfo'")
    
    print("\n4. TEST USER COMMANDS:")
    print("   Send a message to your bot in Telegram")
    print("   Check Railway logs for webhook processing")
    
    print("\n5. RAILWAY LOG COMMANDS:")
    print("   railway logs --follow")
    print("   railway status")

async def main():
    """Main verification and fix process."""
    print("🔍 Railway Deployment Verification")
    print("="*50)
    
    # Load environment variables
    load_dotenv()
    
    # Get Railway URL (you need to provide this)
    railway_url = input("\n📝 Enter your Railway deployment URL (e.g., https://your-app.railway.app): ").strip()
    
    if not railway_url.startswith('http'):
        print("❌ Invalid URL format. Please include http:// or https://")
        return
    
    # Remove trailing slash
    railway_url = railway_url.rstrip('/')
    
    print(f"\n🔍 Testing Railway deployment: {railway_url}")
    
    # Test Railway endpoint
    railway_healthy = await test_railway_endpoint(railway_url)
    
    # Get current webhook info
    print("\n🔍 Checking current webhook configuration...")
    webhook_info = await get_railway_webhook_info()
    
    if webhook_info:
        current_url = webhook_info.get('url', 'Not set')
        pending_update_count = webhook_info.get('pending_update_count', 0)
        last_error = webhook_info.get('last_error_message', 'None')
        
        print(f"📍 Current webhook URL: {current_url}")
        print(f"📊 Pending updates: {pending_update_count}")
        print(f"❗ Last error: {last_error}")
        
        expected_webhook = f"{railway_url}/api/v1/webhook"
        
        if current_url != expected_webhook:
            print(f"\n⚠️ WEBHOOK MISMATCH DETECTED!")
            print(f"   Current: {current_url}")
            print(f"   Expected: {expected_webhook}")
            
            if railway_healthy:
                fix_webhook = input("\n🔧 Fix webhook now? (y/n): ").lower().strip()
                if fix_webhook == 'y':
                    success = await set_railway_webhook(railway_url)
                    if success:
                        print("✅ Webhook fixed! Test user commands now.")
                    else:
                        print("❌ Failed to fix webhook. Check token and try manually.")
            else:
                print("❌ Cannot fix webhook - Railway deployment not healthy")
        else:
            print("✅ Webhook URL is correct")
            
            if pending_update_count > 0:
                print(f"⚠️ Warning: {pending_update_count} pending updates in webhook queue")
    
    # Generate fix commands regardless
    generate_railway_fix_commands(railway_url)
    
    print("\n" + "="*60)
    print("📋 SUMMARY")
    print("="*60)
    
    if railway_healthy:
        print("✅ Railway deployment is healthy")
    else:
        print("❌ Railway deployment has issues")
    
    if webhook_info and webhook_info.get('url', '').endswith('/api/v1/webhook'):
        print("✅ Webhook is configured")
    else:
        print("❌ Webhook needs to be set/updated")
    
    print("\n💡 Next steps:")
    print("1. Ensure Railway environment variables are set correctly")
    print("2. Update webhook URL if needed")
    print("3. Test user commands in Telegram")
    print("4. Monitor Railway logs for webhook processing")

if __name__ == "__main__":
    asyncio.run(main())
