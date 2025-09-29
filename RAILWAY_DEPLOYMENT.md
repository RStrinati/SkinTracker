# Railway Deployment Guide for SkinTracker

## 🚀 Quick Setup via Railway Dashboard

Since the CLI is experiencing timeouts, use the web dashboard:

### 1. Environment Variables
Add these in Railway Dashboard > Your Project > Variables:

```
TELEGRAM_BOT_TOKEN = [Your Telegram Bot Token]
OPENAI_API_KEY = [Your OpenAI API Key]
NEXT_PUBLIC_SUPABASE_URL = [Your Supabase URL]
NEXT_PUBLIC_SUPABASE_ANON_KEY = [Your Supabase Anon Key]
SUPABASE_SERVICE_ROLE_KEY = [Your Supabase Service Role Key]
```

### 2. GitHub Connection
1. Go to your service settings
2. Click "Connect Repo"  
3. Select: `RStrinati/SkinTracker`
4. Set branch: `main`
5. Set root directory: `/` (or leave empty)

### 3. Build Settings
Railway should auto-detect Python and use:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`

### 4. Deploy
After connecting GitHub:
1. Click "Deploy" 
2. Monitor build logs
3. Your app will be available at: `https://your-service-name.railway.app`

### 5. Update Telegram Webhook
Once deployed, update your webhook:
```bash
curl -X POST "https://your-service-name.railway.app/api/v1/set-webhook"
```

## 🔧 Troubleshooting

### Build Issues
- Ensure `requirements.txt` is in root directory
- Check Python version compatibility (Railway uses Python 3.11+)
- Verify all imports work

### Runtime Issues  
- Check environment variables are set correctly
- Monitor deployment logs in Railway dashboard
- Verify Supabase connection works

### Port Issues
- Railway automatically sets `$PORT` environment variable
- Server is configured to bind to `0.0.0.0:$PORT`

## 📊 Monitoring
- View logs in Railway dashboard
- Check metrics and usage
- Set up alerts for downtime

## 💰 Costs
- **Free tier**: $5 monthly credit
- **Usage-based**: Pay for what you use
- **Estimated cost**: $5-15/month for this app
