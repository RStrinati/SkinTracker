#!/bin/bash
set -e

echo "🚀 Deploying SkinTracker to Cloudflare Workers..."

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "📦 Installing Wrangler..."
    npm install -g wrangler
fi

# Login to Cloudflare (if not already logged in)
echo "🔐 Checking Cloudflare authentication..."
if ! wrangler whoami > /dev/null 2>&1; then
    echo "Please login to Cloudflare first:"
    echo "wrangler login"
    exit 1
fi

# Create D1 database if it doesn't exist
echo "📊 Setting up D1 database..."
DB_NAME="skintracker-sessions"

# Try to create database (will fail if it exists, which is fine)
wrangler d1 create "$DB_NAME" || echo "Database might already exist"

# Get the database ID and update wrangler.toml
DB_ID=$(wrangler d1 list | grep "$DB_NAME" | awk '{print $2}' | head -1)
if [ -n "$DB_ID" ]; then
    echo "📝 Found database ID: $DB_ID"
    # Update wrangler.toml with the database ID
    sed -i "s/database_id = \"\"/database_id = \"$DB_ID\"/" wrangler.toml
else
    echo "❌ Could not find database ID"
    exit 1
fi

# Apply database schema
echo "🏗️ Applying database schema..."
wrangler d1 execute "$DB_NAME" --file=./d1-schema.sql

# Set secrets
echo "🔐 Setting up secrets..."

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Enter your Telegram Bot Token:"
    read -s TELEGRAM_BOT_TOKEN
fi
echo "$TELEGRAM_BOT_TOKEN" | wrangler secret put TELEGRAM_BOT_TOKEN

if [ -z "$OPENAI_API_KEY" ]; then
    echo "Enter your OpenAI API Key:"
    read -s OPENAI_API_KEY
fi
echo "$OPENAI_API_KEY" | wrangler secret put OPENAI_API_KEY

if [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "Enter your Supabase Service Role Key:"
    read -s SUPABASE_SERVICE_ROLE_KEY
fi
echo "$SUPABASE_SERVICE_ROLE_KEY" | wrangler secret put SUPABASE_SERVICE_ROLE_KEY

# Deploy to Cloudflare Workers
echo "☁️ Deploying to Cloudflare Workers..."
wrangler deploy

# Get the deployed URL
WORKER_URL=$(wrangler whoami | grep -oP 'https://.*\.workers\.dev' || echo "")

if [ -n "$WORKER_URL" ]; then
    echo "✅ Deployment complete!"
    echo "🌐 Your worker is available at: $WORKER_URL"
    
    # Update Telegram webhook
    echo "🔗 Updating Telegram webhook..."
    curl -X POST "$WORKER_URL/api/v1/set-webhook" || echo "❌ Failed to set webhook - you can do this manually"
    
    echo ""
    echo "🎉 SkinTracker is now live on Cloudflare Workers!"
    echo "📱 Test your bot: https://t.me/your_bot_username"
    echo "🌍 Web interface: $WORKER_URL/timeline"
    echo ""
    echo "Next steps:"
    echo "1. Test the bot by sending /start command"
    echo "2. Upload a skin photo to test analysis"
    echo "3. Check the timeline at $WORKER_URL/timeline"
    echo "4. Monitor logs with: wrangler tail"
else
    echo "❌ Could not determine worker URL"
    echo "Check your deployment with: wrangler whoami"
fi
