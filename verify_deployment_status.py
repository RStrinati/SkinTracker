#!/usr/bin/env python3
"""
Comprehensive deployment verification script for Railway SkinTracker bot.
Checks both external endpoints and Telegram webhook status.
"""

import os
import requests
import json
from datetime import datetime

def check_endpoint(url, method="GET", data=None, timeout=10):
    """Check if an endpoint is responding"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        
        return {
            "status": "success",
            "status_code": response.status_code,
            "response": response.text[:500],  # Limit response size
            "headers": dict(response.headers)
        }
    except requests.exceptions.Timeout:
        return {"status": "timeout", "error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"status": "connection_error", "error": "Connection failed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_telegram_webhook(bot_token):
    """Check Telegram webhook status"""
    if not bot_token:
        return {"status": "error", "error": "No bot token provided"}
    
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {"status": "success", "webhook_info": data.get("result", {})}
        else:
            return {"status": "error", "error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def main():
    print(f"🔍 Railway Deployment Verification - {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Railway deployment URL
    base_url = "https://skintracker-production.up.railway.app"
    
    # Test endpoints
    endpoints = [
        {"name": "Health Check", "url": f"{base_url}/health", "method": "GET"},
        {"name": "API Health", "url": f"{base_url}/api/v1/health", "method": "GET"},
        {"name": "Webhook Test", "url": f"{base_url}/api/v1/webhook", "method": "POST", "data": {"test": "connection"}},
    ]
    
    # Check each endpoint
    for endpoint in endpoints:
        print(f"\n📡 Testing: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        result = check_endpoint(
            endpoint["url"], 
            endpoint.get("method", "GET"), 
            endpoint.get("data")
        )
        
        if result["status"] == "success":
            print(f"   ✅ Status: {result['status_code']}")
            if result.get("response"):
                print(f"   📄 Response: {result['response']}")
        else:
            print(f"   ❌ Failed: {result['status']}")
            if result.get("error"):
                print(f"   🚨 Error: {result['error']}")
    
    # Check Telegram webhook status
    print(f"\n🤖 Checking Telegram Webhook Status")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token:
        webhook_result = check_telegram_webhook(bot_token)
        if webhook_result["status"] == "success":
            webhook_info = webhook_result["webhook_info"]
            print(f"   ✅ Webhook URL: {webhook_info.get('url', 'Not set')}")
            print(f"   📊 Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"   🕐 Last error date: {webhook_info.get('last_error_date', 'None')}")
            if webhook_info.get('last_error_message'):
                print(f"   ⚠️  Last error: {webhook_info['last_error_message']}")
        else:
            print(f"   ❌ Failed to check webhook: {webhook_result.get('error', 'Unknown error')}")
    else:
        print("   ⚠️  TELEGRAM_BOT_TOKEN not set in local environment")
    
    # Summary
    print(f"\n📋 Deployment Status Summary")
    print("=" * 40)
    print("ℹ️  Based on the Railway logs, the build completed successfully")
    print("ℹ️  Internal healthcheck passed: '[1/1] Healthcheck succeeded!'")
    print("ℹ️  External endpoints returning 502: Application running but not accessible")
    print("\n🔧 Next Steps:")
    print("1. Verify environment variables in Railway dashboard")
    print("2. Check SUPABASE_URL and SUPABASE_ANON_KEY are set")
    print("3. Ensure TELEGRAM_BOT_TOKEN is configured")
    print("4. After env vars are set, redeploy or restart the service")
    print("5. Test webhook functionality after successful deployment")

if __name__ == "__main__":
    main()
