#!/usr/bin/env python3
"""
Setup script to help configure Supabase for SkinTracker bot.
This script will help you verify your environment and create the storage bucket.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

def main():
    print("🚀 SkinTracker Supabase Setup Helper")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check environment variables
    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    anon_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    print("\n📋 Environment Variables Check:")
    print(f"✅ SUPABASE_URL: {'✓' if supabase_url else '❌ MISSING'}")
    print(f"✅ ANON_KEY: {'✓' if anon_key else '❌ MISSING'}")
    print(f"✅ SERVICE_ROLE_KEY: {'✓' if service_role_key else '❌ MISSING (Required for bucket creation)'}")
    
    if not supabase_url or not anon_key:
        print("\n❌ Missing required environment variables!")
        print("Please add them to your .env file:")
        print("NEXT_PUBLIC_SUPABASE_URL=your_supabase_url")
        print("NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key")
        print("SUPABASE_SERVICE_ROLE_KEY=your_service_role_key")
        return
    
    # Test connection
    print("\n🔌 Testing Supabase Connection...")
    try:
        client = create_client(supabase_url, service_role_key or anon_key)
        print("✅ Connection successful!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Check/Create storage bucket
    if service_role_key:
        print("\n🪣 Checking Storage Bucket...")
        try:
            bucket = client.storage.get_bucket('skin-photos')
            print("✅ Storage bucket 'skin-photos' already exists!")
        except Exception:
            print("📦 Creating storage bucket 'skin-photos'...")
            try:
                client.storage.create_bucket(
                    'skin-photos',
                    options={
                        "public": False,
                        "file_size_limit": 10 * 1024 * 1024,  # 10 MB
                        "allowed_mime_types": [
                            "image/jpeg",
                            "image/png", 
                            "image/webp",
                        ],
                    },
                )
                print("✅ Storage bucket created successfully!")
            except Exception as e:
                print(f"❌ Failed to create bucket: {e}")
                print("Please create the bucket manually in Supabase Dashboard → Storage")
    else:
        print("\n⚠️  No service role key found.")
        print("Please create the 'skin-photos' bucket manually:")
        print("1. Go to Supabase Dashboard → Storage")
        print("2. Click 'New bucket'")
        print("3. Name: skin-photos")
        print("4. Set as Private")
        print("5. Click 'Create bucket'")
    
    print("\n🎉 Setup complete! Your bot should now be able to handle photo uploads.")
    print("Run 'python server.py' to start your bot.")

if __name__ == "__main__":
    main()
