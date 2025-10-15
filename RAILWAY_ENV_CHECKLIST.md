# Railway Environment Variables Checklist

## ✅ Required Environment Variables

Before deploying to Railway, ensure ALL these variables are set in your Railway dashboard:

### 1. **Telegram Bot** (REQUIRED)
```
TELEGRAM_BOT_TOKEN = <your_telegram_bot_token>
```
Get from [@BotFather](https://t.me/BotFather) on Telegram.

### 2. **Supabase Database** (REQUIRED)
```
NEXT_PUBLIC_SUPABASE_URL = https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
Get from Supabase Dashboard → Project Settings → API

**Alternative (if service role key not available):**
```
NEXT_PUBLIC_SUPABASE_ANON_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. **OpenAI API** (REQUIRED for skin analysis)
```
OPENAI_API_KEY = sk-...
```
Get from [OpenAI Platform](https://platform.openai.com/api-keys)

### 4. **Railway Public URL** (Auto-set after first deploy)
```
BASE_URL = https://your-service.railway.app
```
This is automatically available as `RAILWAY_PUBLIC_DOMAIN`, but you may need to set it manually for webhook registration.

---

## 🔧 How to Set Variables in Railway

### Via Railway Dashboard:
1. Go to your project: https://railway.app/project/[your-project-id]
2. Click on your service
3. Go to **"Variables"** tab
4. Click **"+ New Variable"**
5. Add each variable one by one
6. Click **"Deploy"** to apply changes

### Via Railway CLI:
```bash
railway variables set TELEGRAM_BOT_TOKEN=<your_token>
railway variables set NEXT_PUBLIC_SUPABASE_URL=<your_url>
railway variables set SUPABASE_SERVICE_ROLE_KEY=<your_key>
railway variables set OPENAI_API_KEY=<your_key>
```

---

## ✅ Verification Commands

After setting variables, verify they're loaded correctly:

### Check Railway Variables:
```bash
railway variables
```

### Check Application Logs:
Look for these startup messages in Railway logs:
```
✅ Environment - Railway: True
✅ Bot initialization started
✅ Database connected successfully
✅ Initialized storage bucket: skin-photos
✅ Scheduler started with 2 jobs
```

### Test Health Endpoint:
```bash
curl https://your-service.railway.app/health
```

Expected response:
```json
{"status":"healthy"}
```

---

## 🚨 Common Issues

### Issue: "Bot token not found"
**Fix:** Set `TELEGRAM_BOT_TOKEN` in Railway variables

### Issue: "Supabase connection failed"
**Fix:** Verify `NEXT_PUBLIC_SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are correct

### Issue: "OpenAI API error"
**Fix:** Check `OPENAI_API_KEY` is valid and has credits

### Issue: Webhook registration fails
**Fix:** Set `BASE_URL` to your Railway public domain (e.g., `https://skintracker-production.up.railway.app`)

---

## 📋 Complete Environment Variable Template

Copy this template and fill in your values:

```env
# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# OR (if service role key not available)
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Railway (auto-set, or set manually)
BASE_URL=https://your-service.railway.app

# Optional - Session Management
SESSION_DB_PATH=auth_sessions.db
SESSION_TTL=86400

# Optional - Server Configuration (Railway auto-sets PORT)
# PORT=8080  # Don't set this manually - Railway handles it
# HOST=0.0.0.0
```

---

## 🎯 Next Steps After Setting Variables

1. **Commit and push** the updated Dockerfile and railway.json
2. **Deploy** on Railway (will auto-trigger from GitHub)
3. **Monitor logs** for successful startup
4. **Test health endpoint**: `curl https://your-service.railway.app/health`
5. **Register webhook**: `curl -X POST https://your-service.railway.app/api/v1/set-webhook`
6. **Test bot**: Send `/start` to your Telegram bot

---

## 📞 Support

If deployment still fails after setting all variables:
1. Check Railway logs for specific error messages
2. Verify Supabase database has required tables (users, photos, etc.)
3. Ensure Supabase storage bucket "skin-photos" exists
4. Confirm OpenAI API key has available credits
