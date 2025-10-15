# 🔧 CRITICAL PORT FIX - Railway Deployment

## 🚨 ROOT CAUSE IDENTIFIED

**Problem**: Uvicorn was starting on port **8000** instead of Railway's expected port **8080**

### Evidence from Logs:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

But Railway healthcheck expects:
```
Port configuration: 8080
Healthcheck Path: /health
```

This mismatch caused:
```
Attempt #1 failed with service unavailable. Continuing to retry for 19s
Attempt #2 failed with service unavailable. Continuing to retry for 8s
1/1 replicas never became healthy!
Healthcheck failed!
```

---

## ✅ THE FIX

### Updated `Dockerfile` CMD:

**Before:**
```dockerfile
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0"]
```

**After:**
```dockerfile
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}"]
```

### What This Does:
- `${PORT:-8080}` uses Railway's `PORT` environment variable (8080)
- Fallback to 8080 if `PORT` is not set
- Shell expansion properly resolves the variable

---

## 📊 Deployment Timeline

1. **Previous Attempts** ❌
   - Removed `--port $PORT` thinking it was the issue
   - Uvicorn defaulted to port 8000
   - Railway healthcheck failed (looking for 8080)

2. **Current Fix** ✅
   - Explicitly use `--port ${PORT:-8080}`
   - Uvicorn will start on port 8080
   - Railway healthcheck will succeed

---

## 🎯 Expected Outcome

After this deployment:

1. ✅ Build completes successfully (~40 seconds)
2. ✅ Container starts on port 8080
3. ✅ Uvicorn logs: `Uvicorn running on http://0.0.0.0:8080`
4. ✅ Railway healthcheck succeeds: `[1/1] Healthcheck succeeded!`
5. ✅ External health endpoint returns 200 OK
6. ✅ Bot responds to Telegram commands

---

## 📝 Verification Steps

### 1. Monitor Railway Logs
Look for:
```
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
✅ [1/1] Healthcheck succeeded!
```

### 2. Test Health Endpoint
```bash
curl https://skintracker-production.up.railway.app/health
```

Expected response:
```json
{"status":"healthy"}
```

### 3. Register Telegram Webhook
```bash
curl -X POST https://skintracker-production.up.railway.app/api/v1/set-webhook
```

### 4. Test Bot
Send `/start` to your Telegram bot - it should respond with the main menu.

---

## 🔍 Why This Was Tricky

1. **Internal startup succeeded** - All initialization logs looked perfect
2. **Healthcheck failed externally** - Railway couldn't reach the app
3. **Port mismatch was subtle** - Easy to miss in logs (8000 vs 8080)
4. **Variable expansion confusion** - Removing `--port $PORT` seemed right but caused Uvicorn to default to 8000

---

## 📚 Lessons Learned

- ✅ Always check **exact port** in Uvicorn startup logs
- ✅ Use `${VAR:-default}` syntax for environment variables in shell
- ✅ Don't assume defaults - explicitly set critical values
- ✅ Railway expects app to bind to `$PORT` (usually 8080)

---

## 🚀 Status

**Fix Applied**: ✅ Committed and pushed to `main`  
**Railway Deployment**: 🔄 Auto-deploying now  
**ETA**: ~2-3 minutes

---

## 📞 Next Steps

1. Wait for Railway deployment to complete
2. Check logs for `Uvicorn running on http://0.0.0.0:8080`
3. Verify healthcheck passes
4. Test health endpoint
5. Register webhook
6. Test bot with `/start`

**This should fix the 502 errors! 🎉**
