#!/usr/bin/env python3
"""
Railway Deployment Fix Script
"""
import os
import requests
import json

def check_railway_status():
    """Check if Railway deployment is running."""
    railway_url = "https://skintracker-production.up.railway.app"
    
    print("🔍 Checking Railway deployment status...")
    
    try:
        response = requests.get(f"{railway_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Railway is healthy: {data}")
            return True, railway_url
        else:
            print(f"❌ Railway returned {response.status_code}: {response.text}")
            return False, railway_url
    except requests.exceptions.RequestException as e:
        print(f"❌ Railway connection failed: {e}")
        return False, railway_url

def check_webhook_with_token():
    """Check webhook status using bot token."""
    # You'll need to provide your bot token here
    bot_token = input("Enter your Telegram bot token: ").strip()
    
    if not bot_token:
        print("❌ No bot token provided")
        return None
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            webhook_info = data.get('result', {})
            
            print("\n📍 Current Webhook Configuration:")
            print(f"  URL: {webhook_info.get('url', 'Not set')}")
            print(f"  Pending Updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"  Last Error: {webhook_info.get('last_error_message', 'None')}")
            print(f"  Last Error Date: {webhook_info.get('last_error_date', 'None')}")
            
            return webhook_info, bot_token
        else:
            print(f"❌ Failed to get webhook info: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error checking webhook: {e}")
        return None

def fix_webhook(bot_token, railway_url):
    """Update webhook to point to Railway."""
    webhook_url = f"{railway_url}/api/v1/webhook"
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        response = requests.post(url, json={"url": webhook_url}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"✅ Webhook updated successfully to: {webhook_url}")
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

def main():
    print("🔧 Railway Deployment Fix Tool")
    print("=" * 50)
    
    # Step 1: Check Railway status
    railway_healthy, railway_url = check_railway_status()
    
    # Step 2: Check webhook configuration
    webhook_result = check_webhook_with_token()
    
    if not webhook_result:
        print("\n❌ Cannot proceed without webhook information")
        return
    
    webhook_info, bot_token = webhook_result
    current_webhook = webhook_info.get('url', '')
    expected_webhook = f"{railway_url}/api/v1/webhook"
    
    print(f"\n🔍 Analysis:")
    print(f"  Railway Status: {'✅ Healthy' if railway_healthy else '❌ Down'}")
    print(f"  Current Webhook: {current_webhook}")
    print(f"  Expected Webhook: {expected_webhook}")
    print(f"  Webhook Match: {'✅' if current_webhook == expected_webhook else '❌'}")
    
    # Step 3: Provide recommendations
    print(f"\n📋 Issues Found:")
    
    if not railway_healthy:
        print("❌ Railway deployment is not responding (502 error)")
        print("   This means the application crashed or failed to start")
        print("   Check Railway logs for startup errors")
        print("   Possible causes:")
        print("   - Missing environment variables")
        print("   - Code errors preventing startup")
        print("   - Database connection issues")
    
    if current_webhook != expected_webhook:
        print("❌ Webhook is pointing to wrong URL")
        print(f"   Current: {current_webhook}")
        print(f"   Should be: {expected_webhook}")
        
        if railway_healthy:
            fix_now = input("\n🔧 Railway is healthy. Fix webhook now? (y/n): ").lower().strip()
            if fix_now == 'y':
                fix_webhook(bot_token, railway_url)
        else:
            print("   Cannot fix webhook until Railway deployment is healthy")
    
    # Step 4: Action plan
    print(f"\n🚀 Action Plan:")
    
    if not railway_healthy:
        print("1. Fix Railway deployment first:")
        print(f"   - Check Railway dashboard for your project")
        print(f"   - View deployment logs for errors")
        print(f"   - Ensure environment variables are set:")
        print(f"     BASE_URL=https://skintracker-production.up.railway.app")
        print(f"     RAILWAY_ENVIRONMENT=true")
        print(f"     TELEGRAM_BOT_TOKEN=<your_token>")
        print(f"     SUPABASE_URL=<your_supabase_url>")
        print(f"     SUPABASE_ANON_KEY=<your_supabase_key>")
        print(f"     OPENAI_API_KEY=<your_openai_key>")
        print(f"   - Redeploy if necessary")
    
    if current_webhook != expected_webhook:
        print("2. Update webhook after Railway is healthy:")
        print(f"   curl -X POST 'https://api.telegram.org/bot{bot_token}/setWebhook' \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -d '{{\"url\": \"{expected_webhook}\"}}'")
    
    print("3. Test the fix:")
    print("   - Send a message to your bot")
    print("   - Check Railway logs for webhook processing")
    print("   - Verify user commands work")

if __name__ == "__main__":
    main()
