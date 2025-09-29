# SkinTracker Hybrid Architecture Guide

## 🏗️ Optimal Setup: Railway + Home Server

### Architecture Overview:
```
[User] → [Railway Web App] → [Home Server AI] → [Supabase DB]
```

## 🌐 Railway Responsibilities (Lightweight):
✅ **Web dashboard** - Timeline, user interface  
✅ **Telegram bot** - Message handling, webhooks
✅ **API endpoints** - Authentication, data serving
✅ **Static assets** - Frontend files
✅ **Session management** - User authentication

**Cost**: $5-15/month (very reasonable)

## 🏠 Home Server Responsibilities (Heavy Processing):
✅ **Image analysis** - OpenCV, face detection
✅ **AI processing** - InsightFace, skin analysis  
✅ **ML models** - Local inference
✅ **File storage** - Temporary image processing
✅ **Background jobs** - Queue processing

**Cost**: $0 (your electricity + hardware)

## 🔗 Communication Flow:

### 1. User uploads photo via Telegram
```
User → Railway Bot → Queue job in Supabase → Home Server
```

### 2. Home server processes image
```
Home Server → Downloads image → Analyzes → Uploads results → Supabase
```

### 3. Railway serves results
```
Railway → Fetches results from Supabase → Returns to user
```

## 📊 Implementation Details:

### Railway App (Minimal):
- FastAPI with basic endpoints
- Telegram webhook handling
- Job queue management
- Web dashboard serving
- No OpenCV/heavy dependencies

### Home Server Setup:
- Full Python environment with all CV libraries
- Background worker service
- Polls Supabase for pending jobs
- Can be your existing PC/Raspberry Pi

## 💡 Benefits:
- **99% cost reduction** for image processing
- **Scalable** - Upgrade home hardware as needed
- **Privacy** - Sensitive processing stays local
- **Flexibility** - Test new AI models locally
- **Reliability** - Railway handles web traffic, home handles AI

## 🛠️ Technical Implementation:

### Job Queue Table (Supabase):
```sql
CREATE TABLE analysis_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    image_url TEXT,
    status TEXT DEFAULT 'pending',
    results JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);
```

### Home Server Worker (Python):
```python
# Polls for jobs every 30 seconds
# Downloads images, processes, uploads results
# Updates job status in Supabase
```

### Railway Integration:
```python
# Creates jobs when images received
# Checks job status for results
# Lightweight - no heavy processing
```
