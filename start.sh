#!/bin/sh
set -e

# Railway Startup Script - Optimized for Fast & Reliable Deployment
echo "=========================================="
echo "🚀 SkinTracker Railway Deployment"
echo "=========================================="
echo "📍 PORT: ${PORT:-8080}"
echo "🌍 BASE_URL: ${BASE_URL}"
echo "🔧 Environment: ${RAILWAY_ENVIRONMENT:-production}"
echo "=========================================="
echo ""

# Verify critical environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ ERROR: TELEGRAM_BOT_TOKEN not set!"
    exit 1
fi

if [ -z "$SUPABASE_URL" ]; then
    echo "❌ ERROR: SUPABASE_URL not set!"
    exit 1
fi

if [ -z "$SUPABASE_KEY" ]; then
    echo "❌ ERROR: SUPABASE_KEY not set!"
    exit 1
fi

echo "✅ All critical environment variables present"
echo ""

# Start uvicorn with explicit configuration
echo "🚀 Starting Uvicorn server..."
exec uvicorn server:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --log-level info \
    --access-log \
    --no-use-colors
