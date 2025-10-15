#!/bin/bash

echo "=================================="
echo "🔧 Railway Deployment Fix Script"
echo "=================================="
echo ""

# Kill any running monitor scripts
echo "🛑 Stopping any running monitor scripts..."
pkill -f "monitor_deployment.sh" 2>/dev/null || true
sleep 2

echo ""
echo "📋 Step 1: Verify Railway Project Link"
railway whoami 2>&1 | grep -q "Logged in" && echo "✅ Logged in to Railway" || echo "❌ Not logged in to Railway"

echo ""
echo "📋 Step 2: Check Current Deployment Status"
railway status 2>&1 | head -15

echo ""
echo "📋 Step 3: Verify Environment Variables"
echo "Checking critical environment variables..."
railway variables 2>&1 | grep -E "TELEGRAM_BOT_TOKEN|SUPABASE_URL|BASE_URL|PORT" || echo "⚠️ Could not fetch variables"

echo ""
echo "📋 Step 4: Force New Deployment"
echo "🚀 Triggering fresh deployment..."
railway up --detach

echo ""
echo "📋 Step 5: Wait for Deployment to Build"
sleep 10

echo ""
echo "📋 Step 6: Check Deployment Logs"
railway logs --tail 30

echo ""
echo "📋 Step 7: Test Endpoint"
sleep 5
echo "Testing health endpoint..."
RESPONSE=$(curl -s -w "\n%{http_code}" "https://skintracker-production.up.railway.app/health" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Deployment is LIVE and responding!"
    echo "Response: $(echo "$RESPONSE" | head -1)"
else
    echo "❌ Still getting HTTP $HTTP_CODE"
    echo "Full response: $RESPONSE"
fi

echo ""
echo "=================================="
echo "Fix script completed!"
echo "=================================="
