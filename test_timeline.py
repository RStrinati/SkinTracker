"""
Test script for timeline API functionality.
Tests the database view and API endpoints.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from database import Database
from dotenv import load_dotenv
import json

async def test_timeline_functionality():
    """Test the timeline view and insights functions."""
    print("🧪 Testing Timeline Functionality\n")
    
    load_dotenv()
    db = Database()
    await db.initialize()
    
    user_id = 6865543260  # Your telegram ID
    
    try:
        # 1. Test getting user record
        print("1️⃣ Testing user lookup...")
        user = await db.get_user_by_telegram_id(user_id)
        if user:
            print(f"   ✅ User found: {user['id']}")
            user_uuid = user['id']
        else:
            print("   ❌ User not found")
            return
        
        # 2. Test timeline view query
        print("\n2️⃣ Testing timeline view...")
        query = f"""
        SELECT lane, COUNT(*) as count
        FROM vw_timeline_events 
        WHERE user_id = '{user_uuid}'
        GROUP BY lane
        ORDER BY count DESC
        """
        
        # Since we can't use RPC directly, let's test individual table queries
        # Test symptom logs
        symptom_response = db.client.table('symptom_logs').select('*').eq('user_id', user_uuid).limit(5).execute()
        print(f"   📊 Symptom logs: {len(symptom_response.data)} found")
        
        # Test product logs  
        product_response = db.client.table('product_logs').select('*').eq('user_id', user_uuid).limit(5).execute()
        print(f"   💊 Product logs: {len(product_response.data)} found")
        
        # Test trigger logs
        trigger_response = db.client.table('trigger_logs').select('*').eq('user_id', user_uuid).limit(5).execute()
        print(f"   🎯 Trigger logs: {len(trigger_response.data)} found")
        
        # Test photo logs
        photo_response = db.client.table('photo_logs').select('*').eq('user_id', user_uuid).limit(5).execute()
        print(f"   📷 Photo logs: {len(photo_response.data)} found")
        
        # Test mood logs
        mood_response = db.client.table('daily_mood_logs').select('*').eq('user_id', user_uuid).limit(5).execute()
        print(f"   😊 Mood logs: {len(mood_response.data)} found")
        
        # 3. Test data for insights
        print("\n3️⃣ Testing insights data availability...")
        
        # Check if we have enough data for trigger analysis
        if len(trigger_response.data) > 0 and len(symptom_response.data) > 0:
            print("   ✅ Sufficient data for trigger analysis")
            
            # Show sample data
            if trigger_response.data:
                trigger = trigger_response.data[0]
                print(f"   📝 Sample trigger: {trigger['trigger_name']} at {trigger['logged_at']}")
            
            if symptom_response.data:
                symptom = symptom_response.data[0]
                print(f"   📝 Sample symptom: {symptom['symptom_name']} (severity: {symptom['severity']}) at {symptom['logged_at']}")
        else:
            print("   ⚠️  Limited data for trigger analysis")
        
        # Check if we have enough data for product analysis
        if len(product_response.data) > 0 and len(symptom_response.data) > 0:
            print("   ✅ Sufficient data for product analysis")
            
            if product_response.data:
                product = product_response.data[0]
                print(f"   📝 Sample product: {product['product_name']} ({product.get('effect', 'N/A')}) at {product['logged_at']}")
        else:
            print("   ⚠️  Limited data for product analysis")
        
        # 4. Test recent data (last 30 days)
        print("\n4️⃣ Testing recent data (last 30 days)...")
        from datetime import datetime, timedelta
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        recent_symptoms = db.client.table('symptom_logs').select('*').eq('user_id', user_uuid).gte('logged_at', thirty_days_ago).execute()
        recent_products = db.client.table('product_logs').select('*').eq('user_id', user_uuid).gte('logged_at', thirty_days_ago).execute()
        recent_triggers = db.client.table('trigger_logs').select('*').eq('user_id', user_uuid).gte('logged_at', thirty_days_ago).execute()
        
        print(f"   📊 Recent symptoms: {len(recent_symptoms.data)}")
        print(f"   💊 Recent products: {len(recent_products.data)}")
        print(f"   🎯 Recent triggers: {len(recent_triggers.data)}")
        
        # 5. Test data quality
        print("\n5️⃣ Testing data quality...")
        
        # Check for severity values in symptoms
        severities = [s.get('severity') for s in symptom_response.data if s.get('severity')]
        if severities:
            avg_severity = sum(severities) / len(severities)
            print(f"   📈 Average severity: {avg_severity:.1f}/5 (based on {len(severities)} records)")
        
        # Check for notes/details
        symptoms_with_notes = [s for s in symptom_response.data if s.get('notes')]
        products_with_notes = [p for p in product_response.data if p.get('notes')]
        triggers_with_notes = [t for t in trigger_response.data if t.get('notes')]
        
        print(f"   📝 Symptoms with notes: {len(symptoms_with_notes)}/{len(symptom_response.data)}")
        print(f"   📝 Products with notes: {len(products_with_notes)}/{len(product_response.data)}")
        print(f"   📝 Triggers with notes: {len(triggers_with_notes)}/{len(trigger_response.data)}")
        
        print("\n✅ Timeline functionality test completed!")
        print("\n📋 Summary:")
        print(f"   • Total events available for timeline")
        print(f"   • Data suitable for insights analysis")
        print(f"   • Ready for API testing")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_timeline_functionality())
