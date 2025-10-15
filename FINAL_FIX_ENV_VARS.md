# Railway Environment Variables - FINAL FIX

## ❌ MISSING VARIABLES - ADD THESE NOW:

Go to Railway Dashboard → Variables → Add Variable

### 1. Add SUPABASE_KEY
**Name:** `SUPABASE_KEY`
**Value:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoY2Jhc3p0eG9zY3RuemZ5dmJ1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzk3NzM2NCwiZXhwIjoyMDY5NTUzMzY0fQ.WCNH9QEaGcuYIgGg_mQ1CrTCZzFIgjyhQzy4XO_3K1k`

(Use your SUPABASE_SERVICE_ROLE_KEY value)

### 2. Add SUPABASE_STORAGE_URL
**Name:** `SUPABASE_STORAGE_URL`
**Value:** `https://vhcbasztxosctnzfyvbu.supabase.co/storage/v1`

---

## After Adding These:

Railway will automatically redeploy (takes ~30 seconds).

Then test:
```bash
curl https://skintracker-production.up.railway.app/health
```

Expected: `{"status":"healthy","timestamp":...,"port":8080}`

---

## Why This Will Fix the 502:

Your start.sh script validates environment variables and exits if they're missing:

```bash
if [ -z "$SUPABASE_KEY" ]; then
    echo "❌ ERROR: SUPABASE_KEY not set!"
    exit 1
fi
```

Once you add these variables, the validation will pass and the app will start properly!
