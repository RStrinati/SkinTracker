#!/bin/sh

# Railway Startup Script with Health Check Delay
# This ensures the server is fully ready before Railway starts health checks

echo "🚀 Starting SkinTracker on Railway..."
echo "📍 PORT: ${PORT:-8080}"
echo "🌍 BASE_URL: ${BASE_URL:-not set}"
echo ""

# Start uvicorn in background
uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080} &
UVICORN_PID=$!

echo "⏳ Waiting for server to be ready..."
sleep 5

# Check if process is still running
if kill -0 $UVICORN_PID 2>/dev/null; then
    echo "✅ Server started successfully (PID: $UVICORN_PID)"
    echo "✅ Ready to accept traffic on port ${PORT:-8080}"
    
    # Wait for uvicorn process
    wait $UVICORN_PID
else
    echo "❌ Server failed to start"
    exit 1
fi
