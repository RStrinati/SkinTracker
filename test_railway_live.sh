#!/bin/bash

# Railway Deployment Health Check & Webhook Setup Script

URL="https://skintracker-production.up.railway.app"

echo "🔍 Testing Railway Deployment..."
echo "================================"
echo ""

# Test health endpoint
echo "1️⃣ Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ Health check PASSED (200 OK)"
    echo "   Response: $BODY"
    echo ""
    
    # Register webhook
    echo "2️⃣ Registering Telegram webhook..."
    WEBHOOK_RESPONSE=$(curl -s -X POST "$URL/api/v1/set-webhook")
    echo "   Response: $WEBHOOK_RESPONSE"
    echo ""
    
    # Get webhook info
    echo "3️⃣ Checking webhook info..."
    WEBHOOK_INFO=$(curl -s "$URL/api/v1/webhook-info")
    echo "   Info: $WEBHOOK_INFO"
    echo ""
    
    echo "✅ DEPLOYMENT SUCCESSFUL!"
    echo ""
    echo "📱 Next steps:"
    echo "   1. Open Telegram and find your bot"
    echo "   2. Send /start to test the bot"
    echo "   3. Bot should respond with the main menu"
    
elif [ "$HTTP_CODE" == "502" ]; then
    echo "❌ Health check FAILED (502 Bad Gateway)"
    echo "   Response: $BODY"
    echo ""
    echo "⏳ Railway may still be deploying. Please wait 1-2 minutes and try again."
    echo ""
    echo "🔍 Possible issues:"
    echo "   - Deployment still in progress"
    echo "   - Healthcheck timeout (check Railway dashboard)"
    echo "   - App crashed after startup (check Railway logs)"
    
else
    echo "⚠️  Unexpected response (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
fi

echo ""
echo "🔗 Check Railway dashboard for detailed logs:"
echo "   https://railway.app/project/92621f2e-1240-4dc0-b1fe-135de4780172"
