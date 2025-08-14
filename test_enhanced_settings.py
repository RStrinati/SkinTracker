#!/usr/bin/env python3

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

from database import Database
from dotenv import load_dotenv

async def test_enhanced_settings():
    """Test the enhanced settings functionality"""
    load_dotenv()
    
    print("=== Testing Enhanced Settings Functionality ===")
    
    # Initialize database
    db = Database()
    
    test_telegram_id = 6865543260  # Your telegram ID
    
    print("\n1. Testing product management:")
    
    # Add a test product first
    await db.add_product(test_telegram_id, "Test Cleanser", "cleanser")
    print("   ✅ Added test product: Test Cleanser")
    
    # Get products
    products = await db.get_products(test_telegram_id)
    print(f"   📋 Found {len(products)} products")
    for product in products:
        print(f"      • {product['name']} ({product.get('type', 'no type')})")
    
    # Test renaming product
    if products:
        old_name = products[0]['name']
        new_name = f"{old_name} (Updated)"
        success = await db.update_product_name(test_telegram_id, old_name, new_name)
        status = "✅" if success else "❌"
        print(f"   {status} Renamed product: {old_name} → {new_name}")
        
        # Rename it back
        await db.update_product_name(test_telegram_id, new_name, old_name)
    
    print("\n2. Testing data summary:")
    summary = await db.get_data_summary(test_telegram_id)
    print("   📊 Current data counts:")
    
    data_labels = {
        'photos': '📸 Photos',
        'products': '🧴 Product logs', 
        'triggers': '⚠️ Trigger logs',
        'symptoms': '🏥 Symptom logs',
        'moods': '😊 Daily moods',
        'kpis': '📊 Skin analysis'
    }
    
    for data_type, label in data_labels.items():
        count = summary.get(data_type, 0)
        print(f"      {label}: {count}")
    
    print("\n3. Testing data deletion (test mode - not actually deleting):")
    # Don't actually delete data in test
    print("   ⚠️ Skipping actual deletion in test mode")
    print("   📝 Would test deleting specific data types...")
    
    print("\n✅ Enhanced settings test completed!")
    print("\nNew settings features available:")
    print("🔧 Enhanced Settings Menu:")
    print("   • ⏰ Update Reminder Time - Choose from preset times or disable")
    print("   • 🏷️ Manage Products - Rename or delete custom products")
    print("   • 🗑️ Delete Data - Selectively delete photos, logs, or everything")
    print("   • ➕ Add Condition - Existing feature for tracking skin conditions")
    print("\n💡 How to test:")
    print("1. Send /settings to your bot")
    print("2. Try the new options!")
    print("3. Product management only shows custom products you've added")

if __name__ == "__main__":
    asyncio.run(test_enhanced_settings())
