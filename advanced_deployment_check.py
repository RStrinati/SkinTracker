#!/usr/bin/env python3
"""
Advanced Railway deployment checker with retry logic and detailed diagnostics.
"""

import requests
import time
import json
from datetime import datetime

def check_endpoint_with_retry(url, max_retries=3, timeout=30):
    """Check endpoint with retry logic for deployments"""
    print(f"   🔄 Checking {url}")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"      Attempt {attempt}/{max_retries}...")
            response = requests.get(url, timeout=timeout)
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "response": response.text,
                    "attempt": attempt
                }
            elif response.status_code == 502:
                print(f"      ❌ 502 Error (attempt {attempt})")
                if attempt < max_retries:
                    print(f"      ⏱️  Waiting 10 seconds before retry...")
                    time.sleep(10)
                continue
            else:
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "response": response.text,
                    "attempt": attempt
                }
                
        except requests.exceptions.Timeout:
            print(f"      ⏰ Timeout (attempt {attempt})")
            if attempt < max_retries:
                print(f"      ⏱️  Waiting 15 seconds before retry...")
                time.sleep(15)
        except requests.exceptions.ConnectionError:
            print(f"      🔌 Connection error (attempt {attempt})")
            if attempt < max_retries:
                print(f"      ⏱️  Waiting 15 seconds before retry...")
                time.sleep(15)
        except Exception as e:
            print(f"      ❌ Unexpected error: {e}")
            break
    
    return {"status": "failed", "error": "All retry attempts failed"}

def main():
    print(f"🚀 Advanced Railway Deployment Check - {datetime.now().isoformat()}")
    print("=" * 70)
    print("ℹ️  This will test the deployment with retry logic for ongoing deployments")
    print()
    
    base_url = "https://skintracker-production.up.railway.app"
    
    # Test health endpoint with retries
    print("🏥 Testing Health Endpoint (with retries for deployment)")
    print("-" * 50)
    health_result = check_endpoint_with_retry(f"{base_url}/health", max_retries=3, timeout=30)
    
    if health_result["status"] == "success":
        print(f"   ✅ SUCCESS after {health_result['attempt']} attempt(s)!")
        print(f"   📄 Response: {health_result['response']}")
        
        # If health check succeeds, test other endpoints
        print(f"\n🔗 Testing API Health Endpoint")
        print("-" * 30)
        api_result = check_endpoint_with_retry(f"{base_url}/api/v1/health", max_retries=2, timeout=15)
        
        if api_result["status"] == "success":
            print(f"   ✅ API Health: SUCCESS")
            print(f"   📄 Response: {api_result['response']}")
        else:
            print(f"   ⚠️  API Health: {api_result.get('status', 'unknown')}")
            
    else:
        print(f"   ❌ Health check failed: {health_result.get('error', 'Unknown error')}")
        print(f"\n🔍 Possible reasons:")
        print(f"   • Railway is still deploying with new environment variables")
        print(f"   • Application is starting up (can take 1-3 minutes)")
        print(f"   • Environment variable configuration issue")
        print(f"   • Application crashed during startup")
    
    print(f"\n📊 Deployment Status Summary")
    print("=" * 40)
    
    if health_result["status"] == "success":
        print("🎉 DEPLOYMENT SUCCESSFUL!")
        print("✅ Application is responding to requests")
        print("✅ Environment variables appear to be working")
        print("\n🔧 Next Steps:")
        print("1. Set up Telegram webhook")
        print("2. Test bot functionality")
        print("3. Monitor callback responses")
    else:
        print("⏳ DEPLOYMENT IN PROGRESS OR FAILED")
        print("ℹ️  Environment variables were updated, deployment may be in progress")
        print("\n🔧 Recommended Actions:")
        print("1. Wait 2-3 minutes for deployment to complete")
        print("2. Check Railway dashboard for deployment status")
        print("3. If still failing, check Railway logs for error messages")
        print("4. Verify all required environment variables are set correctly")
        
    print(f"\n⏰ Check completed at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
