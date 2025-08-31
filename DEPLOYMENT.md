# 🚀 SkinTracker Deployment Guide

This guide shows you multiple ways to host your SkinTracker timeline for Telegram WebApp integration.

## 📋 Quick Setup Options

### Option 1: GitHub Pages (Easiest - Static Frontend) ⭐ RECOMMENDED

**Perfect for:** Timeline frontend only, using your existing API

1. **Push to GitHub:**

   ```bash
   git add .
   git commit -m "Add timeline hosting"
   git push origin main
   ```

2. **Enable GitHub Pages:**

   - Go to your GitHub repo settings
   - Navigate to "Pages" section
   - Source: Deploy from branch `main`
   - Folder: `/` (root)
   - Save

3. **Your timeline will be available at:**

   - `https://rstrinati.github.io/SkinTracker/timeline-standalone.html`
   - Access via bot: `/timeline` command → "Open Timeline (GitHub Pages)"

4. **Update your .env:**
   ```env
   BASE_URL=https://rstrinati.github.io/SkinTracker
   ```

### Option 2: Railway (Full-Stack Backend + Frontend) 🚂

**Perfect for:** Complete hosting including API

1. **Create Railway account:** https://railway.app
2. **Connect GitHub repo**
3. **Deploy automatically**
4. **Get your Railway URL:** `https://skintracker-production.up.railway.app`
5. **Update .env:**
   ```env
   BASE_URL=https://skintracker-production.up.railway.app
   ```

### Option 3: Vercel (Frontend) + Railway (Backend) 🔗

**Perfect for:** Separate frontend and backend hosting

**Frontend (Vercel):**

1. Connect to Vercel: https://vercel.com
2. Import GitHub repo
3. Build command: `cp public/timeline-standalone.html dist/index.html`
4. Output directory: `dist`

**Backend (Railway):**

1. Deploy Python server to Railway
2. Update timeline to point to Railway API

## 🎯 Per-User Timeline Features

Your timeline now supports:

✅ **Automatic user detection** from Telegram WebApp
✅ **User ID fallback** via URL parameters
✅ **Dynamic API configuration** based on hosting environment
✅ **Multi-environment support** (localhost, GitHub Pages, Vercel, etc.)

## 🔧 Configuration for Different Hosts

### For GitHub Pages:

```javascript
// Automatically detects and uses:
// API: https://skintracker-api.railway.app (your backend)
// Frontend: https://rstrinati.github.io/SkinTracker
```

### For Vercel:

```javascript
// Uses same-domain API or configured external API
```

### For Railway (Full-stack):

```javascript
// Uses same-domain for both frontend and API
```

## 📱 Bot Integration

Your bot now provides three access methods:

1. **📈 Open Timeline (WebApp)** - Native Telegram integration
2. **🌐 Open Timeline (GitHub Pages)** - Direct browser access
3. **🔗 Open in Browser** - Traditional web link

## 🔒 Security Notes

- User IDs are passed via URL parameters for static hosting
- Telegram WebApp provides secure user verification
- API endpoints remain secured by your backend authentication

## 🚀 Quick Start (Recommended)

1. **Enable GitHub Pages** in your repo settings
2. **Update BASE_URL** in your .env to your GitHub Pages URL
3. **Test with `/timeline` command** in your bot
4. **Access via**: "Open Timeline (GitHub Pages)" button

Your timeline will be live at:
`https://rstrinati.github.io/SkinTracker/timeline-standalone.html`

## 📊 What You Get

- ✅ Per-user timeline data
- ✅ Real-time insights and analytics
- ✅ Responsive design for mobile/desktop
- ✅ Telegram WebApp integration
- ✅ Direct browser access
- ✅ User-specific data filtering
- ✅ Interactive date range selection
- ✅ Multi-lane event visualization

## 🔧 Troubleshooting

**Issue:** Timeline shows no data
**Solution:** Check API URL in browser console, verify user ID parameter

**Issue:** WebApp doesn't open
**Solution:** Ensure HTTPS URL, check Telegram WebApp requirements

**Issue:** CORS errors
**Solution:** Add proper CORS headers to your API server

## 📈 Next Steps

1. Deploy to GitHub Pages (5 minutes)
2. Test `/timeline` command
3. Optionally set up Railway for full-stack hosting
4. Configure custom domain if needed

Your users will have beautiful, personalized timeline access directly through Telegram! 🎉
