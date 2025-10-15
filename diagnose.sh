#!/bin/bash

echo "=========================================="
echo "Railway Deployment Diagnostic Report"
echo "=========================================="
echo ""
echo "Generated: $(date)"
echo ""

echo "📋 1. Testing Health Endpoint"
echo "-------------------------------------------"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}\nTOTAL_TIME:%{time_total}s" "https://skintracker-production.up.railway.app/health" 2>&1)
echo "$HEALTH_RESPONSE"
echo ""

echo "📋 2. Testing Root Endpoint"
echo "-------------------------------------------"
ROOT_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "https://skintracker-production.up.railway.app/" 2>&1)
echo "$ROOT_RESPONSE"
echo ""

echo "📋 3. Testing API Health Endpoint"
echo "-------------------------------------------"
API_HEALTH=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "https://skintracker-production.up.railway.app/api/v1/health" 2>&1)
echo "$API_HEALTH"
echo ""

echo "📋 4. Checking Railway Connection"
echo "-------------------------------------------"
echo "Railway CLI Status:"
railway whoami 2>&1 || echo "⚠️  Railway CLI not authenticated or not working"
echo ""

echo "📋 5. Git Status"
echo "-------------------------------------------"
git log --oneline -5
echo ""
echo "Last commit:"
git log -1 --pretty=format:"%h - %an, %ar : %s" 
echo ""
echo ""

echo "📋 6. Local File Status"
echo "-------------------------------------------"
echo "Dockerfile exists: $([ -f Dockerfile ] && echo '✅ Yes' || echo '❌ No')"
echo "start.sh exists: $([ -f start.sh ] && echo '✅ Yes' || echo '❌ No')"
echo "railway.json exists: $([ -f railway.json ] && echo '✅ Yes' || echo '❌ No')"
echo "requirements-railway.txt exists: $([ -f requirements-railway.txt ] && echo '✅ Yes' || echo '❌ No')"
echo ""
echo "start.sh executable: $([ -x start.sh ] && echo '✅ Yes' || echo '❌ No (fix: chmod +x start.sh)')"
echo ""

echo "📋 7. Network Connectivity Test"
echo "-------------------------------------------"
echo "Testing Railway edge network..."
curl -s -I "https://skintracker-production.up.railway.app/health" 2>&1 | grep -E "HTTP|X-Railway|Server" || echo "No response headers"
echo ""

echo "=========================================="
echo "Diagnostic Complete"
echo "=========================================="
echo ""
echo "📤 NEXT STEPS:"
echo ""
echo "1. Share this output with your developer/assistant"
echo "2. Go to Railway Dashboard: https://railway.app/project/92621f2e-1240-4dc0-b1fe-135de4780172"
echo "3. Check the latest deployment logs"
echo "4. Verify environment variables are set"
echo ""
echo "If health endpoint returns 502:"
echo "  → Check Railway dashboard deployment logs"
echo "  → Verify all environment variables are set"
echo "  → Try manual redeploy from dashboard"
echo ""
