#!/usr/bin/env python3
"""
Quick test script to run after Railway deployment completes
"""

import requests
import time

def test_deployment():
    print("🚀 Testing Railway Deployment After Variable Update")
    print("=" * 50)
    
    url = "https://skintracker-production.up.railway.app/health"
    
    try:
        response = requests.get(url, timeout=15)
        print(f"✅ Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code == 200:
            print("\n🎉 SUCCESS! Deployment is working!")
            print("🔧 Next step: Set up Telegram webhook")
            return True
        else:
            print(f"\n❌ Still not working. Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_deployment()
