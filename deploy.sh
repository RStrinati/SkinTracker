#!/bin/bash

echo "🚀 Deploying to Railway..."
echo ""

# Stop monitor script if running
pkill -f "monitor_deployment.sh" 2>/dev/null || true
sleep 1

# Deploy
echo "📦 Building and deploying..."
railway up --detach

echo ""
echo "⏳ Waiting 15 seconds for deployment to complete..."
sleep 15

echo ""
echo "📋 Recent logs:"
railway logs --tail 20

echo ""
echo "🔍 Testing endpoint..."
sleep 3

RESPONSE=$(curl -s -w "\n%{http_code}" "https://skintracker-production.up.railway.app/health")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

echo ""
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ SUCCESS! Deployment is live!"
    echo "Response: $(echo "$RESPONSE" | head -1)"
    echo ""
    echo "🎯 Next step: Set webhook"
    echo "Run: curl -X POST https://skintracker-production.up.railway.app/api/v1/set-webhook"
else
    echo "⚠️  HTTP Status: $HTTP_CODE"
    echo "Response: $RESPONSE"
    echo ""
    echo "🔄 The deployment may still be initializing. Wait 30 seconds and test again:"
    echo "curl https://skintracker-production.up.railway.app/health"
fi
