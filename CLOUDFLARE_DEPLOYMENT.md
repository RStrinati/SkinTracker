# SkinTracker - Cloudflare Deployment Guide

This guide covers deploying SkinTracker to Cloudflare Workers with D1 database.

## 📋 Prerequisites

1. **Cloudflare Account** - Sign up at [cloudflare.com](https://cloudflare.com)
2. **Wrangler CLI** - Install with `npm install -g wrangler`
3. **API Tokens** - Telegram Bot Token, OpenAI API Key, Supabase keys

## 🚀 Quick Deployment

### Option 1: Automated Script
```bash
chmod +x deploy-cloudflare.sh
./deploy-cloudflare.sh
```

### Option 2: Manual Steps

1. **Install Wrangler and Login**
   ```bash
   npm install -g wrangler
   wrangler login
   ```

2. **Create D1 Database**
   ```bash
   wrangler d1 create skintracker-sessions
   ```

3. **Update Database ID**
   - Copy the database ID from the output
   - Update `wrangler.toml` with the database ID

4. **Apply Schema**
   ```bash
   wrangler d1 execute skintracker-sessions --file=./d1-schema.sql
   ```

5. **Set Secrets**
   ```bash
   echo "YOUR_BOT_TOKEN" | wrangler secret put TELEGRAM_BOT_TOKEN
   echo "YOUR_OPENAI_KEY" | wrangler secret put OPENAI_API_KEY  
   echo "YOUR_SUPABASE_KEY" | wrangler secret put SUPABASE_SERVICE_ROLE_KEY
   ```

6. **Deploy**
   ```bash
   wrangler deploy
   ```

## 🔧 Configuration

### Environment Variables
Set these as Cloudflare Workers secrets:
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `OPENAI_API_KEY` - OpenAI API key for analysis
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key

### Database Configuration
The app uses Cloudflare D1 database for:
- User session management
- Message queuing
- User preferences
- Rate limiting

## 📊 Monitoring

### View Logs
```bash
wrangler tail
```

### Database Operations
```bash
# List tables
wrangler d1 execute skintracker-sessions --command="SELECT name FROM sqlite_master WHERE type='table';"

# Check sessions
wrangler d1 execute skintracker-sessions --command="SELECT COUNT(*) FROM auth_sessions;"
```

## 🔄 Updates

### Deploy Updates
```bash
git push origin main  # Triggers GitHub Actions
# OR
wrangler deploy       # Manual deployment
```

### Update Secrets
```bash
echo "NEW_VALUE" | wrangler secret put SECRET_NAME
```

## 🌐 Custom Domain (Optional)

1. Add domain to Cloudflare
2. Update `wrangler.toml`:
   ```toml
   [[route]]
   pattern = "yourdomain.com/*"
   zone_name = "yourdomain.com"
   ```
3. Deploy: `wrangler deploy`

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check D1 database is created and ID is correct in `wrangler.toml`
   - Verify schema was applied: `wrangler d1 execute skintracker-sessions --file=./d1-schema.sql`

2. **Secrets Not Available**
   - List secrets: `wrangler secret list`
   - Re-set missing secrets: `echo "value" | wrangler secret put SECRET_NAME`

3. **Webhook Issues**
   - Check worker URL: `wrangler whoami`
   - Manually set webhook: `curl -X POST "https://your-worker.workers.dev/api/v1/set-webhook"`

4. **Import Errors**
   - Some Python packages may not work in Workers runtime
   - Check `requirements-cloudflare.txt` for compatible versions

### Monitoring
- Use `wrangler tail` to see real-time logs
- Check Cloudflare Dashboard > Workers & Pages > Your Worker > Metrics

## 📈 Scaling

Cloudflare Workers automatically scale based on usage:
- **Free Plan**: 100,000 requests/day
- **Paid Plan**: 10M+ requests/month
- **D1 Database**: 100k reads/writes per day (free)

## 🔒 Security

- All secrets are encrypted at rest
- Environment variables are not logged
- D1 database is isolated per account
- HTTPS enforced by default

## 📝 Next Steps

1. Test your deployment: `https://your-worker.workers.dev/health`
2. Update Telegram webhook to point to your Worker
3. Test bot functionality with `/start` command
4. Monitor logs and performance in Cloudflare Dashboard
