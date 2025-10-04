# Railway Deployment Issue Resolution Guide

## Problem Summary
The Railway deployment is returning a 502 error because essential environment variables are missing, preventing the application from starting properly. The scheduled messages are being sent, but responses aren't being registered because the webhook isn't working due to the deployment failure.

## Root Cause
1. **Missing Environment Variables**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and other required variables are not set in Railway
2. **Application Startup Failure**: Without these variables, the bot cannot connect to the database and fails to start
3. **502 Error**: Railway returns 502 when the application fails to respond to health checks

## Solution Steps

### 1. Set Environment Variables in Railway Dashboard

**Required Variables:**
```bash
TELEGRAM_BOT_TOKEN=<your_bot_token>
SUPABASE_URL=<your_supabase_project_url>
SUPABASE_ANON_KEY=<your_supabase_anon_key>
SUPABASE_SERVICE_ROLE_KEY=<your_supabase_service_role_key>
OPENAI_API_KEY=<your_openai_api_key>
BASE_URL=https://skintracker-production.up.railway.app
PORT=8080
RAILWAY_ENVIRONMENT=production
```

**How to set them:**
1. Go to https://railway.app/dashboard
2. Select your SkinTracker project
3. Click on "Variables" tab
4. Add each variable with its value

### 2. Verify Supabase Configuration

Make sure your Supabase project has:
- Tables created (run the schema.sql)
- Proper RLS policies configured
- Storage bucket 'skin-photos' created

### 3. Redeploy Application

After setting environment variables:
1. Trigger a new deployment in Railway
2. Monitor deployment logs for any errors
3. Wait for deployment to complete successfully

### 4. Test Health Endpoint

Once deployed, test:
```bash
curl https://skintracker-production.up.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "timestamp": <timestamp>,
  "services": {
    "database": "ok",
    "bot": "ok",
    "environment": "railway"
  }
}
```

### 5. Set Webhook with Telegram

After successful deployment:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -d "url=https://skintracker-production.up.railway.app/api/v1/webhook"
```

### 6. Verify Webhook

Check webhook status:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## Expected Behavior After Fix

1. **Scheduled Messages**: Will continue to be sent at the configured reminder times
2. **User Responses**: Clicking rating buttons (😃 Excellent, 🙂 Good, etc.) will:
   - Log the mood rating to the database
   - Show confirmation message to user
   - Update user's daily mood tracking

3. **Database Logging**: Responses will be stored in the `daily_mood_logs` table

## Verification Steps

1. **Test Bot Commands**: Send `/start` to your bot
2. **Test Reminders**: Wait for scheduled reminder or set a test reminder
3. **Test Responses**: Click rating buttons in reminder message
4. **Check Database**: Verify entries in `daily_mood_logs` table
5. **Check Progress**: Use `/progress` command to see mood statistics

## Troubleshooting

If issues persist after following these steps:

1. **Check Railway Logs**:
   ```bash
   railway logs
   ```

2. **Check Database Connection**:
   - Verify Supabase credentials
   - Test database queries in Supabase dashboard

3. **Check Bot Configuration**:
   - Verify bot token is valid
   - Check bot permissions with @BotFather

4. **Check Webhook Status**:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```

## Common Error Patterns

- **502 Bad Gateway**: Application not starting (missing env vars)
- **404 Not Found**: Incorrect webhook URL
- **Database Connection Error**: Invalid Supabase credentials
- **Bot Token Error**: Invalid or expired Telegram bot token

The callback handling code in your bot is correct and should work once the deployment issues are resolved.
