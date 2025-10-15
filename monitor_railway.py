#!/usr/bin/env python3
"""
Monitor Railway deployment status after Supabase restart
"""
import requests
import time
import sys

def check_railway_status():
    """Check Railway deployment status."""
    railway_url = "https://skintracker-production.up.railway.app"
    
    print(f"🔍 Monitoring Railway deployment: {railway_url}")
    print("   Waiting for deployment to restart after Supabase recovery...")
    print("   (Press Ctrl+C to stop monitoring)")
    
    attempt = 1
    while True:
        try:
            print(f"\n⏰ Attempt {attempt} - {time.strftime('%H:%M:%S')}")
            
            # Test health endpoint
            response = requests.get(f"{railway_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Railway is HEALTHY!")
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   Services: {data.get('services', {})}")
                
                # Now test webhook endpoint
                print(f"\n🔗 Testing webhook endpoint...")
                webhook_response = requests.get(f"{railway_url}/api/v1/webhook", timeout=5)
                if webhook_response.status_code == 405:  # Method not allowed (expected for GET on POST endpoint)
                    print(f"✅ Webhook endpoint is responding (405 Method Not Allowed is expected)")
                else:
                    print(f"📍 Webhook endpoint status: {webhook_response.status_code}")
                
                print(f"\n🎉 RAILWAY IS READY!")
                print(f"   Next step: Update Telegram webhook")
                print(f"   Command: curl -X POST \"https://api.telegram.org/bot8307648462:AAHrxYiHs965oD_0W0EWUm4Yo3zo3i03YQM/setWebhook\" \\")
                print(f"            -H \"Content-Type: application/json\" \\")
                print(f"            -d '{{\"url\": \"{railway_url}/api/v1/webhook\"}}'")
                break
                
            elif response.status_code == 502:
                print(f"❌ Railway still down (502 - Application failed to respond)")
                print(f"   Supabase is online, Railway needs restart/redeploy")
                
            else:
                print(f"❓ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:100]}...")
                
        except requests.exceptions.Timeout:
            print(f"⏱️ Request timeout - Railway may be restarting")
        except requests.exceptions.ConnectionError:
            print(f"🔌 Connection error - Railway is not responding")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        attempt += 1
        print(f"   Waiting 30 seconds before next check...")
        time.sleep(30)

if __name__ == "__main__":
    try:
        check_railway_status()
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Monitoring stopped by user")
        print(f"💡 To manually check Railway status:")
        print(f"   curl https://skintracker-production.up.railway.app/health")
        sys.exit(0)
