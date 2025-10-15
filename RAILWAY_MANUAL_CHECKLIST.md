# Railway Manual Deployment Checklist

## 🚨 CRITICAL: Do These Steps in Railway Dashboard

Your deployment is returning 502 errors. Follow these steps in the Railway dashboard to diagnose and fix:

### Step 1: Access Railway Dashboard
Go to: https://railway.app/project/92621f2e-1240-4dc0-b1fe-135de4780172

---

### Step 2: Check Deployment Status

1. Click on your **skintracker** service
2. Look at the **Deployments** tab
3. Check the status of the latest deployment:
   - ✅ **Building** - Wait for it to complete
   - ✅ **Deploying** - Wait for it to complete  
   - ✅ **Success** - Deployment is live
   - ❌ **Failed** - Click to see error logs

**What to look for:**
- Is the latest deployment from the last few minutes?
- Does it show "Success" or is it still building?
- Are there multiple deployments? (Delete old ones if yes)

---

### Step 3: Check Deployment Logs

1. Click on the **LATEST deployment**
2. Click **"View Logs"** or the **Logs** tab
3. Scroll to the bottom to see recent output

**Look for these messages:**
```
✅ GOOD SIGNS:
- "🚀 Starting SkinTracker..."
- "PORT: 8080"
- "INFO: Uvicorn running on http://0.0.0.0:8080"
- "✅ READY TO ACCEPT TRAFFIC ON PORT 8080"
- "Bot initialized successfully"
- "GET /health HTTP/1.1" 200 OK

❌ BAD SIGNS:
- "Error during startup"
- "Failed to create bot instance"
- "Connection refused"
- "TELEGRAM_BOT_TOKEN not set"
- "SUPABASE_URL not set"
- Any stack traces or error messages
```

**Action:** Copy and paste the last 30 lines of logs to share with me.

---

### Step 4: Verify Environment Variables

1. In the service view, click **"Variables"** tab
2. Verify ALL these variables are set:

```
Required Variables:
✅ TELEGRAM_BOT_TOKEN = 8307648462:AAHrx... (your bot token)
✅ SUPABASE_URL = https://vhcbasztxosctnzfyvbu.supabase.co
✅ SUPABASE_KEY = (your supabase key - starts with "eyJ...")
✅ SUPABASE_STORAGE_URL = https://vhcbasztxosctnzfyvbu.supabase.co/storage/v1
✅ OPENAI_API_KEY = sk-proj-... (your OpenAI key)
✅ BASE_URL = https://skintracker-production.up.railway.app

Auto-set by Railway:
✅ PORT = (should be auto-set, don't manually set this)
✅ RAILWAY_ENVIRONMENT = production (auto-set)
```

**Action:** 
- If any are missing, click "+ New Variable" to add them
- After adding variables, Railway will automatically redeploy

---

### Step 5: Check Service Settings

1. Click **"Settings"** tab
2. Verify these settings:

**Build Configuration:**
- Builder: **Dockerfile** (not Nixpacks)
- Dockerfile Path: `Dockerfile`
- Watch Paths: (leave default or empty)

**Deploy Configuration:**
- Health Check Path: `/health`
- Health Check Timeout: `100` seconds
- Restart Policy: `On Failure`

**Networking:**
- Public Networking: **Enabled** ✅
- Domain should show: `skintracker-production.up.railway.app`

**Action:** If any settings are wrong, update them and click "Deploy" to trigger new deployment.

---

### Step 6: Force Redeploy

If everything looks correct but still getting 502:

1. Go to **Deployments** tab
2. Find the latest **successful** deployment
3. Click the **three dots (...)** menu
4. Select **"Redeploy"**
5. Wait 30-60 seconds for deployment to complete

---

### Step 7: Test the Endpoints

After deployment completes, test these URLs in your browser:

**Health Check:**
```
https://skintracker-production.up.railway.app/health
```
Expected: `{"status":"healthy","timestamp":...,"port":8080}`

**Root Endpoint:**
```
https://skintracker-production.up.railway.app/
```
Expected: `{"message":"Skin Health Tracker Bot is running..."}`

**API Health:**
```
https://skintracker-production.up.railway.app/api/v1/health
```
Expected: `{"status":"healthy","services":{"database":"ok"},...}`

---

### Step 8: Set Telegram Webhook

Once health checks pass (you get 200 OK responses), set the webhook:

**Option A: Use Browser**
Visit this URL:
```
https://skintracker-production.up.railway.app/api/v1/set-webhook
```

**Option B: Use curl**
```bash
curl -X POST https://skintracker-production.up.railway.app/api/v1/set-webhook
```

Expected response:
```json
{
  "success": true,
  "webhook_url": "https://skintracker-production.up.railway.app/api/v1/telegram-webhook",
  "webhook_set": true
}
```

---

### Step 9: Verify Webhook is Set

Check webhook status:
```
https://skintracker-production.up.railway.app/api/v1/webhook-info
```

Expected:
```json
{
  "url": "https://skintracker-production.up.railway.app/api/v1/telegram-webhook",
  "has_custom_certificate": false,
  "pending_update_count": 0,
  ...
}
```

---

### Step 10: Test Bot in Telegram

1. Open Telegram
2. Find your bot: **@yourbotname** (or search for it)
3. Send: `/start`
4. Expected: Bot should respond with welcome message and menu

---

## 🐛 Troubleshooting Based on Logs

### If logs show: "ModuleNotFoundError" or "ImportError"
**Problem:** Missing Python packages
**Fix:** 
- Check `requirements-railway.txt` includes all needed packages
- Trigger redeploy after fixing

### If logs show: "TELEGRAM_BOT_TOKEN not set"
**Problem:** Environment variable missing
**Fix:** 
- Add variable in Railway dashboard
- Railway will auto-redeploy

### If logs show: "Connection refused" or "Database error"
**Problem:** Supabase connection issue
**Fix:** 
- Verify SUPABASE_URL and SUPABASE_KEY are correct
- Check Supabase dashboard that project is active

### If logs show: "Port 8080 already in use"
**Problem:** Multiple deployments running
**Fix:** 
- Delete all but the latest deployment
- Redeploy

### If logs show nothing after "Starting SkinTracker..."
**Problem:** Application crashing during initialization
**Fix:** 
- Check for Python syntax errors
- Review bot.py initialization code
- Share full logs for detailed help

---

## 📋 Information to Collect

Please share these details so I can help further:

1. **Latest Deployment Status:**
   - Is it "Success", "Failed", or "Building"?
   - Deployment ID (shown in logs)

2. **Last 30 Lines of Logs:**
   - Copy from Railway dashboard logs
   - Include timestamp if available

3. **Environment Variables:**
   - Confirm all required ones are set (don't share the actual values)
   - Are there any extra variables that might conflict?

4. **Health Check Response:**
   - What happens when you visit the health URL in browser?
   - HTTP status code (200, 502, 404, etc.)

5. **Settings:**
   - Builder type (Dockerfile or Nixpacks?)
   - Health check timeout value

---

## ✅ Success Criteria

Your deployment is working when:

✅ Health endpoint returns 200 OK with JSON response
✅ Logs show "Uvicorn running on http://0.0.0.0:8080"
✅ Logs show "Bot initialized successfully"
✅ Webhook set successfully
✅ Bot responds to /start in Telegram

---

## 🚀 Quick Recovery Steps

If you're stuck, try this sequence:

1. **Delete all deployments** except the latest
2. **Verify all environment variables** are set correctly
3. **Force redeploy** from Railway dashboard
4. **Wait 60 seconds** for deployment to complete
5. **Test health endpoint** in browser
6. If 200 OK → **Set webhook** → **Test in Telegram**
7. If still 502 → **Share logs** for advanced troubleshooting

---

## Need Help?

Share with me:
- Screenshot of deployment status
- Last 30 lines of logs
- Result when visiting health URL in browser

I'll analyze and provide specific fixes!
