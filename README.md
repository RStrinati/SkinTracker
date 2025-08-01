# 🌟 Skin Health Tracker Bot

A Python-based Telegram bot that helps users track their skin health journey with AI-powered insights, photo analysis, and comprehensive logging capabilities.

## 📋 Features

### 🤖 Telegram Bot Interface
- **User-friendly commands**: `/start`, `/log`, `/summary`, `/help`
- **Interactive keyboards**: Tap buttons to log products, triggers, and symptoms
- **Photo uploads**: Upload skin photos with AI analysis
- **Personalized insights**: Weekly summaries powered by GPT-4

### 📊 Comprehensive Tracking
- **Products**: Log skincare products and track effectiveness
- **Triggers**: Record environmental and lifestyle factors
- **Symptoms**: Rate severity on 1-5 scale (redness, bumps, dryness, etc.)
- **Photos**: Visual progress tracking with AI analysis

### 🔒 Secure & Private
- **Row Level Security**: Each user only accesses their own data
- **Private photo storage**: Images stored securely in Supabase
- **Telegram integration**: No additional login required

## 🚀 Quick Start

### 1. Environment Setup

Visit `/env-check` page to configure required environment variables:

- **NEXT_PUBLIC_SUPABASE_URL**: Your Supabase project URL
- **NEXT_PUBLIC_SUPABASE_ANON_KEY**: Supabase anonymous key
- **TELEGRAM_BOT_TOKEN**: Bot token from @BotFather
- **OPENAI_API_KEY**: OpenAI API key for GPT-4 analysis

### 2. Database Setup

1. Create a new Supabase project at [supabase.com](https://supabase.com)
2. Run the SQL schema in Supabase SQL Editor:
   ```bash
   # Copy contents of schema.sql into Supabase SQL Editor
   ```
3. This creates all necessary tables and Row Level Security policies

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 4. Run the Application

```bash
# Start FastAPI server
python server.py

# Or with uvicorn for production
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 5. Set Webhook

```bash
# Set webhook URL for your bot
curl -X POST http://localhost:8000/set-webhook
```

## 🏗️ Architecture

### Backend Stack
- **FastAPI**: High-performance Python web framework
- **python-telegram-bot**: Telegram Bot API integration
- **Supabase**: PostgreSQL database and file storage
- **OpenAI GPT-4**: AI-powered analysis and insights

### Database Schema
- `users`: Telegram user profiles
- `product_logs`: Skincare product usage
- `trigger_logs`: Skin irritation triggers
- `symptom_logs`: Symptom severity ratings
- `photo_logs`: Photos with AI analysis

### File Structure
```
├── server.py           # FastAPI application and webhook handler
├── bot.py             # Telegram bot logic and commands
├── database.py        # Supabase database operations
├── openai_service.py  # OpenAI GPT-4 integration
├── schema.sql         # Database schema and RLS policies
├── requirements.txt   # Python dependencies
└── .env              # Environment variables
```

## 🤖 Bot Commands

### `/start`
- Register new user
- Welcome message with feature overview

### `/log`
- Interactive logging menu with buttons:
  - 📷 Add Photo
  - 🧴 Log Product
  - ⚡ Log Trigger  
  - 📊 Rate Symptoms

### `/summary`
- AI-generated weekly progress report
- Insights about product effectiveness
- Trigger pattern analysis
- Personalized recommendations

### `/help`
- Detailed explanation of logging types
- Best practices for tracking
- Photography tips

## 📷 Photo Analysis

The bot accepts skin photos and provides:
- **AI-powered analysis**: General observations about skin appearance
- **Progress tracking**: Visual comparison over time
- **Photography tips**: Guidance for consistent documentation
- **Secure storage**: Private cloud storage with user-only access

## 🔐 Security Features

### Row Level Security (RLS)
- Users can only access their own data
- Database-level security enforcement
- Automatic policy application

### Private Storage
- Photos stored in private Supabase bucket
- User-specific access controls
- Secure URL generation

### Data Privacy
- No sensitive data logged
- AI analysis keeps photos private
- User data isolation

## 📊 Logging Categories

### 🧴 Products
Predefined options include:
- Cicaplast, Azelaic Acid, Enstilar
- Cerave Moisturizer, Sunscreen
- Retinol, Niacinamide, Salicylic Acid
- Custom "Other" option

### ⚡ Triggers  
Common skin irritation factors:
- Environmental: Sun, Weather, Pollution
- Lifestyle: Stress, Sleep, Diet, Exercise
- Skincare: New Products, Application changes

### 📈 Symptoms
Rate severity 1-5 for:
- Redness, Bumps, Dryness
- Stinging, Itching, Burning
- Tightness, Flaking, Irritation

## 🤖 AI-Powered Insights

### Weekly Summaries
- Overall skin health trends
- Product effectiveness analysis
- Trigger pattern identification
- Severity change tracking
- Personalized recommendations

### Photo Analysis
- Visual progress assessment
- Skin appearance observations
- Photography improvement tips
- Progress encouragement

### Smart Recommendations
- Product suggestions based on data
- Routine optimization tips
- Trigger avoidance strategies

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Fill in your API keys

# Run development server
python server.py
```

### Production Deployment
```bash
# Use production WSGI server
pip install gunicorn
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Testing Webhook
```bash
# Set webhook
curl -X POST https://your-domain.com/set-webhook

# Test webhook
curl -X POST https://your-domain.com/webhook \\
  -H "Content-Type: application/json" \\
  -d '{"test": "webhook"}'
```

## 📈 Analytics & Insights

The bot tracks and analyzes:
- **Usage patterns**: Most common products and triggers
- **Severity trends**: Symptom improvement over time  
- **Photo progress**: Visual skin health changes
- **Routine effectiveness**: Product correlation with symptoms

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
1. Check the `/help` command in the bot
2. Review environment variable setup at `/env-check`
3. Verify Supabase database schema
4. Ensure all API keys are correctly configured

## 🌟 Features Roadmap

- [ ] Multi-language support
- [ ] Advanced photo comparison
- [ ] Routine recommendations
- [ ] Data export functionality
- [ ] Integration with health apps

---

Built with ❤️ for better skin health tracking through technology.