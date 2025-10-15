#!/bin/bash

echo "🔄 Monitoring Railway Deployment Status..."
echo "==========================================="
echo ""

URL="https://skintracker-production.up.railway.app/health"
MAX_ATTEMPTS=30
SLEEP_INTERVAL=10

echo "Testing endpoint: $URL"
echo "Will check every $SLEEP_INTERVAL seconds for up to $MAX_ATTEMPTS attempts"
echo ""

for i in $(seq 1 $MAX_ATTEMPTS); do
    echo -n "[$i/$MAX_ATTEMPTS] Testing... "
    
    RESPONSE=$(curl -s -w "\n%{http_code}" "$URL" 2>&1)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    
    if [ "$HTTP_CODE" == "200" ]; then
        echo "✅ SUCCESS!"
        echo ""
        echo "Response: $BODY"
        echo ""
        echo "🎉 DEPLOYMENT IS LIVE!"
        echo ""
        echo "Next steps:"
        echo "  1. Register webhook:"
        echo "     curl -X POST $URL/../set-webhook"
        echo "  2. Test bot in Telegram with /start"
        exit 0
    else
        echo "❌ HTTP $HTTP_CODE (still waiting...)"
        if [ $i -lt $MAX_ATTEMPTS ]; then
            sleep $SLEEP_INTERVAL
        fi
    fi
done

echo ""
echo "⚠️  Deployment still not accessible after $((MAX_ATTEMPTS * SLEEP_INTERVAL)) seconds"
echo ""
echo "This suggests a Railway configuration issue. Try:"
echo "  1. Check Railway dashboard for deployment status"
echo "  2. Look for multiple active deployments"
echo "  3. Try restarting the service in Railway dashboard"
