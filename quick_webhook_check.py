#!/usr/bin/env python3
"""
Quick webhook status check
"""
import os
import requests
from dotenv import load_dotenv

def check_webhook_status():
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return
    
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            webhook_info = data.get('result', {})
            
            print("🔍 Current Webhook Status:")
            print(f"  URL: {webhook_info.get('url', 'Not set')}")
            print(f"  Pending Updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"  Last Error: {webhook_info.get('last_error_message', 'None')}")
            print(f"  Max Connections: {webhook_info.get('max_connections', 'Default')}")
            
            webhook_url = webhook_info.get('url', '')
            if 'ngrok' in webhook_url:
                print("\n⚠️  ISSUE DETECTED: Webhook is pointing to ngrok (local development)")
                print("   This explains why user commands aren't working on Railway!")
                print("   The webhook needs to be updated to your Railway URL.")
            elif 'railway' in webhook_url or 'up.railway.app' in webhook_url:
                print("\n✅ Webhook appears to be pointing to Railway")
                if webhook_info.get('pending_update_count', 0) > 0:
                    print("⚠️  But there are pending updates - webhook may not be working")
            else:
                print(f"\n❓ Unknown webhook URL pattern: {webhook_url}")
        else:
            print(f"❌ Failed to get webhook info: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking webhook: {e}")

if __name__ == "__main__":
    check_webhook_status()
