#!/bin/sh

# Railway Startup Script
echo "🚀 Starting SkinTracker..."
echo "PORT: ${PORT:-8080}"

# Start uvicorn directly
exec uvicorn server:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --log-level info \
    --access-log
