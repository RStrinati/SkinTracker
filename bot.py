import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import traceback
import time

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode, ChatAction
from telegram.error import RetryAfter, BadRequest

from database import Database
from openai_service import OpenAIService
from reminder_scheduler import ReminderScheduler
# from analysis_providers.insightface_provider import InsightFaceProvider
from skin_analysis import process_skin_image
from skin_kpi_analyzer import SkinKPIAnalyzer

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class SkinHealthBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        self.application = Application.builder().token(self.token).build()
        self.bot = None  # Will be set after initialization
        self.database = Database()
        self.openai_service = OpenAIService()
        self.scheduler: Optional[ReminderScheduler] = None
        # self.analysis_provider = InsightFaceProvider()  # Temporarily disabled
        self.analysis_provider = None

        # Default fallback options if database tables are empty
        self.default_products = [
            "Cicaplast", "Azelaic Acid", "Enstilar", "Cerave Moisturizer",
            "Sunscreen", "Retinol", "Niacinamide", "Salicylic Acid"
        ]

        self.default_triggers = [
            "Sun exposure",
            "Stress",
            "Hot weather",
            "Sweating",
            "Spicy food",
            "Alcohol",
        ]

        self.symptoms = [
            "Redness",
            "Bumps",
            "Itching",
            "Dryness",
            "Burning",
            "Other",
        ]
        
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up command and callback handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("log", self.log_command))
        self.application.add_handler(CommandHandler("summary", self.summary_command))
        # Extra UX commands
        self.application.add_handler(CommandHandler("progress", self.progress_command))
        self.application.add_handler(CommandHandler("skin", self.skin_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Timeline and quick logging commands
        self.application.add_handler(CommandHandler("timeline", self.timeline_command))
        self.application.add_handler(CommandHandler("trigger", self.quick_trigger_command))
        self.application.add_handler(CommandHandler("symptom", self.quick_symptom_command))
        self.application.add_handler(CommandHandler("product", self.quick_product_command))
        
        # Callback query handlers
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Photo handler
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Text message handler for severity rating
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

    async def _setup_persistent_menu(self):
        """Configure bot command list for quick access."""
        commands = [
            BotCommand("log", "📝 Log an entry"),
            BotCommand("timeline", "📈 View timeline"),
            BotCommand("progress", "📊 View progress"),
            BotCommand("skin", "🔬 Skin analysis"),
            BotCommand("settings", "⚙️ Settings"),
        ]
        await self.bot.set_my_commands(commands)
        await self.bot.set_chat_menu_button()

    async def initialize(self):
        """Initialize the bot and database."""
        await self.database.initialize()
        await self.application.initialize()  # Initialize but don't start polling
        # Don't call application.start() for webhook mode - it starts polling
        self.bot = self.application.bot  # Make sure this is after `initialize()`
        await self._setup_persistent_menu()
        # Initialize reminder scheduler now that bot is available
        self.scheduler = ReminderScheduler(self.bot)

        # Reload any stored reminder schedules so they persist across restarts
        users = await self.database.get_users_with_reminders()
        for user in users:
            reminder_time = user.get("reminder_time")
            if reminder_time:
                self.scheduler.schedule_daily_reminder(
                    user["telegram_id"], reminder_time, user.get("timezone", "UTC")
                )

        logger.info("Bot initialized successfully")

    async def shutdown(self):
        """Cleanup resources."""
        # Don't call application.stop() since we didn't start polling
        await self.application.shutdown()
        await self.database.close()
        if self.scheduler:
            self.scheduler.shutdown()
        logger.info("Bot shut down successfully")

    async def send_main_menu(self, update: Update):
        """Send enhanced main menu with static flow."""
        keyboard = [
            [
                InlineKeyboardButton("� Photo Check-in", callback_data="quick_photo"),
                InlineKeyboardButton("📝 Daily Log", callback_data="daily_checkin")
            ],
            [
                InlineKeyboardButton("📊 Progress", callback_data="menu_progress"),
                InlineKeyboardButton("🧠 Insights", callback_data="menu_summary")
            ],
            [
                InlineKeyboardButton("🧴 Products", callback_data="area_products"),
                InlineKeyboardButton("🎯 Areas", callback_data="area_management")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
                InlineKeyboardButton("❓ Help", callback_data="menu_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = update.message or update.callback_query.message
        await message.reply_text(
            "🏠 *Main Menu*\n\nWhat would you like to do?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )


    async def process_update(self, update_data: dict) -> None:
        if not self.application.bot:
            raise RuntimeError("Bot not initialized yet")

        try:
            update = Update.de_json(update_data, self.application.bot)
            await self.application.update_queue.put(update)  # returns immediately
        except Exception:
            logger.exception("Failed to enqueue Telegram update")


    async def set_webhook(self, webhook_url: str) -> bool:
        """Set webhook URL."""
        try:
            await self.bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            return False

    async def delete_webhook(self) -> bool:
        """Delete webhook URL."""
        try:
            await self.bot.delete_webhook()
            logger.info("Webhook deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete webhook: {e}")
            return False

    async def start_command(self, update: Update, context):
        """Handle /start command - enhanced onboarding flow."""
        user = update.effective_user
        telegram_id = user.id
        
        try:
            # Check if user exists
            existing_user = await self.database.get_user_by_telegram_id(telegram_id)
            
            if existing_user:
                # Returning user - show quick menu
                await self._show_returning_user_welcome(update, user.first_name)
                return
            
            # New user - start onboarding
            await self.database.create_user(
                telegram_id=telegram_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            welcome_message = f"""🌟 *Welcome to SkinTrack, {user.first_name}!*

I'm here to help you understand and improve your skin health through intelligent tracking and insights.

*What I'll help you with:*
� **Smart Analysis** - AI-powered skin photo analysis
📈 **Progress Tracking** - Visual timeline of your skin journey  
🧴 **Product Testing** - Track what works (and what doesn't)
⚠️ **Trigger Detection** - Identify what affects your skin
💡 **Personalized Insights** - Weekly reports and recommendations

Let's get you set up for success! 🚀"""
            
            keyboard = [
                [InlineKeyboardButton("✨ Let's Get Started!", callback_data="onboarding_start")],
                [InlineKeyboardButton("📚 Learn More", callback_data="onboarding_learn")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                welcome_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.exception("Error in start command")
            await update.message.reply_text(
                "Sorry, there was an error setting up your account. Please try again."
            )

    async def _show_returning_user_welcome(self, update: Update, first_name: str):
        """Show quick welcome for returning users."""
        message = f"👋 Welcome back, {first_name}!\n\nWhat would you like to do today?"
        
        keyboard = [
            [
                InlineKeyboardButton("📸 Quick Photo", callback_data="quick_photo"),
                InlineKeyboardButton("📝 Daily Check-in", callback_data="daily_checkin")
            ],
            [
                InlineKeyboardButton("📊 View Progress", callback_data="menu_progress"),
                InlineKeyboardButton("🧠 Weekly Summary", callback_data="menu_summary")
            ],
            [InlineKeyboardButton("📋 Full Menu", callback_data="show_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)

    async def log_command(self, update: Update, context):
        """Handle /log command - show logging options."""
        keyboard = [
            [
                InlineKeyboardButton("📷 Add Photo", callback_data="log_photo"),
                InlineKeyboardButton("🧴 Log Product", callback_data="log_product"),
            ],
            [
                InlineKeyboardButton("⚡ Log Trigger", callback_data="log_trigger"),
                InlineKeyboardButton("📊 Log Symptoms", callback_data="log_symptom"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = update.message or update.callback_query.message
        await message.reply_text(
            "What would you like to log today?",
            reply_markup=reply_markup,
        )

    async def summary_command(self, update: Update, context):
        """Handle /summary command - generate AI summary."""
        user_id = update.effective_user.id

        try:
            # Get user's recent logs
            recent_logs = await self.database.get_user_logs(user_id, days=7)

            message = update.message or update.callback_query.message

            if not recent_logs:
                await message.reply_text(
                    "You don't have any logs from the past week. Start logging to get insights!"
                )
                await self.send_main_menu(update)
                return

            # Generate AI summary
            summary = await self.openai_service.generate_summary(recent_logs)

            await message.reply_text(
                f"📈 *Your Weekly Skin Health Summary*\n\n{summary}",
                parse_mode=ParseMode.MARKDOWN,
            )
            await self.send_main_menu(update)

        except Exception as e:
            logger.exception("Error generating summary")
            message = update.message or update.callback_query.message
            await message.reply_text(
                "Sorry, I couldn't generate your summary right now. Please try again later."
            )
            await self.send_main_menu(update)

    async def progress_command(self, update: Update, context):
        """Handle /progress command - show user statistics and skin progress."""
        user_id = update.effective_user.id
        try:
            # Get traditional stats
            stats = await self.database.get_user_stats(user_id, days=30)
            
            # Get skin KPI progress
            kpi_analyzer = SkinKPIAnalyzer(self.database)
            skin_summary = await kpi_analyzer.get_progress_summary(user_id, days=30)
            
            # Build the progress message
            text = "📊 *30-day Progress Overview*\n\n"
            
            # Traditional logging stats
            text += "📝 *Activity Summary:*\n"
            text += f"• Products logged: {stats.get('product_count', 0)}\n"
            text += f"• Triggers logged: {stats.get('trigger_count', 0)}\n"
            text += f"• Symptoms logged: {stats.get('symptom_count', 0)}\n"
            text += f"• Photos uploaded: {stats.get('photo_count', 0)}\n\n"
            
            # Daily mood/feeling stats
            mood_stats = await self.database.get_mood_stats(user_id, days=30)
            if mood_stats.get('total_entries', 0) > 0:
                text += "😊 *Daily Mood Tracking:*\n"
                text += f"• Check-ins: {mood_stats['total_entries']}\n"
                text += f"• Average: {mood_stats['average_rating']:.1f}/5.0\n"
                text += f"• Trend: {mood_stats['trend']}\n"
                
                # Show most common mood
                mood_dist = mood_stats.get('mood_distribution', {})
                if mood_dist:
                    most_common = max(mood_dist.items(), key=lambda x: x[1])
                    text += f"• Most common: {most_common[0]} ({most_common[1]}x)\n"
                text += "\n"
            
            # Skin KPI analysis
            if "message" in skin_summary:
                # Not enough data for skin progress
                text += "📸 *Skin Progress:*\n"
                text += f"{skin_summary['message']}\n"
                text += "_Upload more photos to track your skin improvement!_"
            else:
                # We have skin progress data
                blemish = skin_summary["blemish_improvement"]
                photos = skin_summary["total_photos"]
                
                if blemish["improved"]:
                    emoji = "✅"
                    direction = "Improvement"
                    change_text = f"↓ {abs(blemish['change']):.1f}%"
                else:
                    emoji = "⚠️"
                    direction = "Increase"
                    change_text = f"↑ {blemish['change']:.1f}%"
                
                text += f"🎯 *Skin Progress Analysis:* {emoji}\n"
                text += f"📸 Photos analyzed: {photos}\n"
                text += f"📅 Period: {skin_summary['date_range']['start'][:10]} to {skin_summary['date_range']['end'][:10]}\n\n"
                
                text += f"🔍 *Blemish Analysis:*\n"
                text += f"• Current: {blemish['current_percent']:.1f}%\n"
                text += f"• Initial: {blemish['initial_percent']:.1f}%\n"
                text += f"• Change: {change_text}\n"
                text += f"• Average: {skin_summary['average_blemish_percent']:.1f}%\n\n"
                
                text += f"📏 *Face Area Metrics:*\n"
                text += f"• Current: {skin_summary['face_area']['current_px']:,} pixels\n"
                text += f"• Initial: {skin_summary['face_area']['initial_px']:,} pixels\n\n"
                
                text += f"{emoji} *Overall {direction.lower()}* detected in skin condition!"
            
            message = update.message or update.callback_query.message
            await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            await self.send_main_menu(update)
            
        except Exception as e:
            logger.exception("Error getting progress")
            message = update.message or update.callback_query.message
            await message.reply_text("Sorry, I couldn't load your progress right now.")
            await self.send_main_menu(update)

    async def skin_command(self, update: Update, context):
        """Handle /skin command - show detailed skin analysis and trends."""
        user_id = update.effective_user.id
        try:
            kpi_analyzer = SkinKPIAnalyzer(self.database)
            
            # Get recent KPIs
            recent_kpis = await kpi_analyzer.get_user_kpis(user_id, days=30)
            
            if not recent_kpis:
                text = "📸 *Skin Analysis*\n\n"
                text += "No skin photos found in the last 30 days.\n"
                text += "Upload a photo to start tracking your skin health!"
                
                message = update.message or update.callback_query.message
                await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                await self.send_main_menu(update)
                return
            
            # Get detailed analysis
            skin_summary = await kpi_analyzer.get_progress_summary(user_id, days=30)
            weekly_trends = await kpi_analyzer.get_weekly_trends(user_id, weeks=4)
            
            text = "🔬 *Detailed Skin Analysis*\n\n"
            
            # Latest photo metrics
            latest = recent_kpis[0]  # Most recent photo
            text += f"📸 *Latest Photo Analysis:*\n"
            text += f"• Date: {latest['timestamp'][:10]}\n"
            text += f"• Face Area: {latest['face_area_px']:,} pixels\n"
            text += f"• Blemish Area: {latest['blemish_area_px']:,} pixels\n"
            text += f"• Blemish Percentage: {latest['percent_blemished']:.1f}%\n\n"
            
            # Progress summary
            if "message" not in skin_summary:
                blemish = skin_summary["blemish_improvement"]
                trend_emoji = "📈" if blemish["improved"] else "📉"
                
                text += f"{trend_emoji} *30-Day Progress:*\n"
                text += f"• Photos analyzed: {skin_summary['total_photos']}\n"
                text += f"• Average blemish %: {skin_summary['average_blemish_percent']:.1f}%\n"
                text += f"• Change: {blemish['change']:+.1f}%\n\n"
            
            # Weekly trends
            if weekly_trends:
                text += "📊 *Weekly Trends:*\n"
                for trend in weekly_trends[-3:]:  # Last 3 weeks
                    week_date = trend['week_start']
                    avg_blemish = trend['avg_blemish_percent']
                    photo_count = trend['photo_count']
                    text += f"• Week of {week_date}: {avg_blemish:.1f}% ({photo_count} photos)\n"
                text += "\n"
            
            text += "💡 *Tip:* Upload photos regularly to track your skin improvement over time!"
            
            message = update.message or update.callback_query.message
            await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            await self.send_main_menu(update)
            
        except Exception as e:
            logger.exception("Error getting skin analysis")
            message = update.message or update.callback_query.message
            await message.reply_text("Sorry, I couldn't load your skin analysis right now.")
            await self.send_main_menu(update)

    async def _show_settings(self, update: Update, context):
        """Display settings including existing conditions."""
        user_id = update.effective_user.id
        conditions = await self.database.get_conditions(user_id)
        if conditions:
            cond_lines = [
                f"• {c['name']} ({c['condition_type']})" for c in conditions
            ]
            condition_text = "\n".join(cond_lines)
        else:
            condition_text = "No conditions set."

        # Get current reminder settings
        user = await self.database.get_user_by_telegram_id(user_id)
        reminder_time = user.get('reminder_time', '09:00') if user else '09:00'
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Condition", callback_data="settings_add_condition")],
            [InlineKeyboardButton("⏰ Update Reminder Time", callback_data="settings_reminder")],
            [InlineKeyboardButton("🏷️ Manage Products", callback_data="settings_products")],
            [InlineKeyboardButton("🗑️ Delete Data", callback_data="settings_delete_data")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = update.message or update.callback_query.message
        await message.reply_text(
            f"⚙️ *Settings*\n\n"
            f"*Current Reminder:* {reminder_time}\n\n"
            f"*Your Conditions:*\n{condition_text}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

    async def settings_command(self, update: Update, context):
        """Handle /settings command."""
        await self._show_settings(update, context)

    async def _show_reminder_settings(self, query, context):
        """Show reminder time settings."""
        keyboard = [
            [InlineKeyboardButton("🌅 09:00", callback_data="set_reminder_09:00")],
            [InlineKeyboardButton("🏙️ 12:00", callback_data="set_reminder_12:00")],
            [InlineKeyboardButton("🌆 18:00", callback_data="set_reminder_18:00")],
            [InlineKeyboardButton("🌙 21:00", callback_data="set_reminder_21:00")],
            [InlineKeyboardButton("❌ Disable", callback_data="set_reminder_disable")],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⏰ *Reminder Settings*\n\nChoose when you'd like to receive daily skin check-in reminders:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def _show_product_management(self, query, context, user_id):
        """Show product management options."""
        all_products = await self.database.get_products(user_id)
        
        # Filter to only show user-specific products (not global ones)
        products = [p for p in all_products if not p.get('is_global', True)]
        
        if not products:
            await query.edit_message_text(
                "🏷️ *Product Management*\n\nNo custom products found. Products are automatically added when you log them.\n\n"
                "Use the main menu to log products, and they'll appear here for management.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="settings_back")]])
            )
            return

        keyboard = []
        for product in products[:8]:  # Limit to 8 products to avoid button limit
            keyboard.append([InlineKeyboardButton(
                f"✏️ {product['name']}", 
                callback_data=f"edit_product_{product['name'].replace(' ', '_')}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="settings_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🏷️ *Product Management*\n\nSelect a product to rename or delete ({len(products)} custom products):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def _show_delete_data_options(self, query, context, user_id):
        """Show data deletion options with counts."""
        # Get data summary
        summary = await self.database.get_data_summary(user_id)
        
        text = "🗑️ *Delete Data*\n\n"
        text += "⚠️ *Warning: This action cannot be undone!*\n\n"
        text += "*Your current data:*\n"
        
        data_labels = {
            'photos': '📸 Photos',
            'products': '🧴 Product logs', 
            'triggers': '⚠️ Trigger logs',
            'symptoms': '🏥 Symptom logs',
            'moods': '😊 Daily moods',
            'kpis': '📊 Skin analysis'
        }
        
        for data_type, label in data_labels.items():
            count = summary.get(data_type, 0)
            text += f"• {label}: {count}\n"
        
        keyboard = [
            [InlineKeyboardButton("📸 Delete Photos Only", callback_data="delete_data_photos")],
            [InlineKeyboardButton("📝 Delete Logs Only", callback_data="delete_data_logs")],
            [InlineKeyboardButton("🗑️ Delete Everything", callback_data="delete_data_all")],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def help_command(self, update: Update, context):
        """Handle /help command - show comprehensive help."""
        help_text = """📚 *SkinTrack Help Guide*

🎯 **Core Features:**

📸 **Photo Check-ins**
• Upload clear, well-lit photos
• Try to use consistent lighting & angle
• AI analyzes progress over time

📝 **Daily Logging**  
• Track symptoms (severity 1-5)
• Note triggers affecting your skin
• Record product usage

🎯 **Area Tracking**
• Focus on specific skin areas
• Compare improvement across zones
• Get targeted insights

🧴 **Product Management**
• Test what works for your skin
• Track product effectiveness
• Get usage recommendations

📊 **Progress & Insights**
• View your improvement timeline
• Get AI-powered weekly reports
• Identify patterns and trends

*🏆 Pro Tips:*
• Log daily for best results
• Take photos in similar conditions
• Be consistent with timing
• Track triggers immediately

*📱 Quick Commands:*
/start - Main menu
/log - Quick logging
/progress - View improvements  
/help - This guide

Questions? Just ask! 💬"""
        
        keyboard = [
            [InlineKeyboardButton("🏠 Main Menu", callback_data="show_main_menu")],
            [InlineKeyboardButton("🚀 Quick Start Guide", callback_data="quick_start_guide")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    # ========== NEW ENHANCED FEATURES ==========

    async def _handle_onboarding(self, query, context):
        """Handle onboarding flow for new users."""
        data = query.data
        
        if data == "onboarding_start":
            await self._show_onboarding_step_1(query, context)
        elif data == "onboarding_learn":
            await self._show_onboarding_learn_more(query, context)
        elif data == "onboarding_reminder":
            await self._show_onboarding_reminder_setup(query, context)
        elif data == "onboarding_areas":
            await self._show_onboarding_area_setup(query, context)
        elif data == "onboarding_complete":
            await self._complete_onboarding(query, context)

    async def _show_onboarding_step_1(self, query, context):
        """Step 1: Explain the tracking process."""
        text = """🎯 *Your Skin Journey Starts Here*

*Here's how SkinTrack works:*

🔬 **Week 1-2: Baseline**
• Upload 2-3 photos to establish your starting point
• Log any current products you're using
• Note triggers as they happen

📈 **Week 3+: Track Progress**  
• Continue daily logging
• Watch your progress timeline grow
• Get weekly insights and recommendations

💡 **The Secret:** Consistency beats perfection! Even 30 seconds a day makes a huge difference.

Ready to set up your tracking preferences?"""

        keyboard = [
            [InlineKeyboardButton("✅ Yes, Let's Set Up!", callback_data="onboarding_reminder")],
            [InlineKeyboardButton("🔄 Tell Me More", callback_data="onboarding_learn")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def _show_onboarding_learn_more(self, query, context):
        """Show detailed explanation of features."""
        text = """🧠 *Why SkinTrack Works*

**🔬 Smart Analysis**
• AI compares your photos over time
• Tracks blemish reduction, texture improvement
• Identifies patterns you might miss

**📊 Data-Driven Insights**  
• Correlates products with skin improvements
• Identifies your personal trigger patterns
• Provides actionable recommendations

**🎯 Focused Tracking**
• Track specific problem areas
• See progress where it matters most
• Get targeted treatment suggestions

**💡 Personalized Reports**
• Weekly summaries of your progress
• Product effectiveness analysis
• Next steps for improvement

*Real Results:* Users see 40% better skin improvement when tracking consistently vs. guessing! 📈"""

        keyboard = [
            [InlineKeyboardButton("🚀 I'm Ready to Start!", callback_data="onboarding_reminder")],
            [InlineKeyboardButton("📱 Quick Demo", callback_data="show_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def _show_onboarding_reminder_setup(self, query, context):
        """Set up daily reminder during onboarding."""
        text = """⏰ *Daily Check-in Reminder*

*When would you like your daily skin check-in reminder?*

Choose a time when you typically:
• Have good lighting for photos
• Can spend 1-2 minutes logging
• Are in your usual environment

*📱 You'll get a gentle reminder to:*
• Rate how your skin feels today
• Log any new products or triggers  
• Take a quick progress photo"""

        keyboard = [
            [
                InlineKeyboardButton("🌅 Morning (9 AM)", callback_data="set_reminder_09:00"),
                InlineKeyboardButton("🏙️ Midday (12 PM)", callback_data="set_reminder_12:00")
            ],
            [
                InlineKeyboardButton("🌆 Evening (6 PM)", callback_data="set_reminder_18:00"),
                InlineKeyboardButton("🌙 Night (9 PM)", callback_data="set_reminder_21:00")
            ],
            [InlineKeyboardButton("⏭️ Skip for Now", callback_data="onboarding_areas")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def _show_onboarding_area_setup(self, query, context):
        """Set up tracking areas during onboarding."""
        text = """🎯 *Focus Areas (Optional)*

*Want to track specific problem areas?*

You can focus on particular areas like:
• Forehead acne
• Cheek redness  
• T-zone oiliness
• Chin breakouts

*Benefits:*
• More targeted insights
• Compare improvement across areas
• Specialized recommendations

*You can always add or change these later in Settings.*"""

        keyboard = [
            [InlineKeyboardButton("🎯 Set Up Areas", callback_data="area_setup_new")],
            [InlineKeyboardButton("⏭️ Skip - Track Everything", callback_data="onboarding_complete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def _complete_onboarding(self, query, context):
        """Complete onboarding flow."""
        user_id = query.from_user.id
        
        # Mark user as onboarded
        await self.database.update_user_onboarding_status(user_id, True)
        
        text = """🎉 *You're All Set!*

Welcome to your skin health journey! Here's what to do next:

**📸 Take Your First Photo**
• Upload a baseline photo to start tracking
• Use good lighting and a consistent angle

**📝 Start Daily Logging**  
• Rate how your skin feels today
• Log any products you're currently using

**🔍 Explore Your Tools**
• Check out the Progress section
• Review help for detailed guides

*🏆 Pro Tip:* The first week is about establishing your baseline. Don't worry about perfect photos - consistency matters more!

Ready to start your journey?"""

        keyboard = [
            [InlineKeyboardButton("📸 Take First Photo", callback_data="quick_photo")],
            [InlineKeyboardButton("📝 Daily Check-in", callback_data="daily_checkin")],
            [InlineKeyboardButton("🏠 Explore Menu", callback_data="show_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def _handle_daily_checkin(self, query, context):
        """Handle daily check-in flow."""
        user_id = query.from_user.id
        
        # Get today's existing logs to show progress
        today_logs = await self.database.get_today_logs(user_id)
        
        # Determine what's been done today
        has_photo = today_logs.get('photo_count', 0) > 0
        has_mood = today_logs.get('mood_count', 0) > 0
        has_symptoms = today_logs.get('symptom_count', 0) > 0
        has_products = today_logs.get('product_count', 0) > 0
        
        text = "📝 *Daily Check-in*\n\n"
        text += "*Today's Progress:*\n"
        text += f"📸 Photo: {'✅' if has_photo else '⭕'}\n" 
        text += f"😊 Mood: {'✅' if has_mood else '⭕'}\n"
        text += f"📊 Symptoms: {'✅' if has_symptoms else '⭕'}\n"
        text += f"🧴 Products: {'✅' if has_products else '⭕'}\n\n"
        
        if has_photo and has_mood and has_symptoms:
            text += "🎉 *Great job!* You've completed today's check-in.\n\n"
            text += "Want to add anything else?"
        else:
            text += "*What would you like to log today?*"

        keyboard = []
        
        if not has_photo:
            keyboard.append([InlineKeyboardButton("📸 Add Photo", callback_data="checkin_photo")])
        
        if not has_mood:
            keyboard.append([InlineKeyboardButton("😊 Rate Today's Skin", callback_data="checkin_mood")])
            
        if not has_symptoms:
            keyboard.append([InlineKeyboardButton("📊 Log Symptoms", callback_data="checkin_symptoms")])
            
        keyboard.append([InlineKeyboardButton("🧴 Add Products", callback_data="checkin_products")])
        keyboard.append([InlineKeyboardButton("⚠️ Note Triggers", callback_data="checkin_triggers")])
        
        if has_photo and has_mood and has_symptoms:
            keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="show_main_menu")])
        else:
            keyboard.append([InlineKeyboardButton("⏭️ Finish Later", callback_data="show_main_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def _handle_area_management(self, query, context):
        """Handle area tracking management."""
        user_id = query.from_user.id
        data = query.data
        
        if data == "area_management":
            await self._show_area_overview(query, context, user_id)
        elif data == "area_setup_new":
            await self._show_area_setup(query, context)
        elif data.startswith("area_select_"):
            area_name = data.replace("area_select_", "").replace("_", " ")
            await self._toggle_area_selection(query, context, area_name)
        elif data == "area_save_selection":
            await self._save_area_selection(query, context, user_id)
        elif data.startswith("area_view_"):
            area_name = data.replace("area_view_", "").replace("_", " ")
            await self._show_area_details(query, context, user_id, area_name)

    async def _show_area_overview(self, query, context, user_id):
        """Show overview of user's tracked areas."""
        areas = await self.database.get_user_areas(user_id)
        
        if not areas:
            text = """🎯 *Area Tracking*

*No specific areas set up yet.*

You can track specific problem areas to get more targeted insights:

• **Forehead** - Track acne, oiliness
• **Cheeks** - Monitor redness, texture  
• **T-Zone** - Focus on pores, shine
• **Chin/Jaw** - Track hormonal breakouts
• **Custom Areas** - Name your own zones

*Benefits:*
✅ Focused progress tracking
✅ Area-specific recommendations  
✅ Compare improvement across zones"""

            keyboard = [
                [InlineKeyboardButton("🎯 Set Up Areas", callback_data="area_setup_new")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="show_main_menu")]
            ]
        else:
            text = f"🎯 *Your Tracked Areas* ({len(areas)})\n\n"
            
            for area in areas:
                recent_logs = area.get('recent_log_count', 0)
                text += f"• **{area['name']}** - {recent_logs} recent logs\n"
            
            text += "\n*Select an area to view detailed progress:*"
            
            keyboard = []
            for area in areas:
                keyboard.append([InlineKeyboardButton(
                    f"📊 {area['name']}", 
                    callback_data=f"area_view_{area['name'].replace(' ', '_')}"
                )])
            
            keyboard.append([InlineKeyboardButton("➕ Add New Area", callback_data="area_setup_new")])
            keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="show_main_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def _show_area_setup(self, query, context):
        """Show area setup with common options."""
        text = """🎯 *Set Up Tracking Areas*

*Select the areas you want to focus on:*

Choose areas where you want detailed progress tracking and targeted insights."""

        context.user_data['selected_areas'] = context.user_data.get('selected_areas', [])
        selected = context.user_data['selected_areas']
        
        common_areas = [
            "Forehead", "Left Cheek", "Right Cheek", "Nose", 
            "T-Zone", "Chin", "Jawline", "Under Eyes"
        ]
        
        keyboard = []
        for area in common_areas:
            prefix = "✅ " if area in selected else ""
            keyboard.append([InlineKeyboardButton(
                f"{prefix}{area}",
                callback_data=f"area_select_{area.replace(' ', '_')}"
            )])
        
        keyboard.append([InlineKeyboardButton("💾 Save Selection", callback_data="area_save_selection")])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="area_management")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def _toggle_area_selection(self, query, context, area_name):
        """Toggle area selection during setup."""
        selected = context.user_data.get('selected_areas', [])
        
        if area_name in selected:
            selected.remove(area_name)
        else:
            selected.append(area_name)
        
        context.user_data['selected_areas'] = selected
        
        # Refresh the area setup view
        await self._show_area_setup(query, context)

    async def _save_area_selection(self, query, context, user_id):
        """Save selected areas to database."""
        selected = context.user_data.get('selected_areas', [])
        
        if not selected:
            await query.answer("Please select at least one area to track.")
            return
        
        # Save areas to database
        success_count = 0
        for area_name in selected:
            success = await self.database.create_user_area(user_id, area_name)
            if success:
                success_count += 1
        
        # Clear selection from context
        context.user_data.pop('selected_areas', None)
        
        text = f"""✅ *Areas Saved!*

Successfully set up {success_count} tracking areas:

{chr(10).join(f'• {area}' for area in selected)}

*Next Steps:*
• Use daily check-ins to log area-specific symptoms
• Take photos focusing on these areas
• Get targeted insights in your weekly reports"""

        keyboard = [
            [InlineKeyboardButton("📝 Start Daily Check-in", callback_data="daily_checkin")],
            [InlineKeyboardButton("🎯 Manage Areas", callback_data="area_management")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="show_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def handle_callback(self, update: Update, context):
        """Handle inline keyboard button callbacks."""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id

        # ========== CORE NAVIGATION ==========
        if data == "show_main_menu":
            await self.send_main_menu(update)
            return

        # ========== ONBOARDING FLOW ==========
        if data.startswith("onboarding_"):
            await self._handle_onboarding(query, context)
            return

        # ========== DAILY CHECK-IN FLOW ==========
        if data == "daily_checkin":
            await self._handle_daily_checkin(query, context)
            return
        
        if data.startswith("checkin_"):
            await self._handle_checkin_actions(query, context)
            return

        # ========== QUICK ACTIONS ==========
        if data == "quick_photo":
            await query.edit_message_text(
                "📸 *Quick Photo Check-in*\n\n"
                "Upload a clear, well-lit photo of your skin.\n\n"
                "*💡 Tips:*\n"
                "• Use consistent lighting\n"
                "• Same angle as previous photos\n"
                "• Clean skin (no makeup)\n\n"
                "Ready? Upload your photo now! 📷",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ========== AREA MANAGEMENT ==========
        if data.startswith("area_"):
            await self._handle_area_management(query, context)
            return

        # ========== MAIN MENU OPTIONS ==========
        if data.startswith("menu_"):
            if data == "menu_log":
                await self.log_command(update, context)
            elif data == "menu_progress":
                await self.progress_command(update, context)
            elif data == "menu_summary":
                await self.summary_command(update, context)
            elif data == "menu_settings":
                await self._show_settings(update, context)
            elif data == "menu_help":
                await self.help_command(update, context)
            return

        # ========== PRODUCT MANAGEMENT ==========
        if data == "area_products":
            await self._show_product_management(query, context, user_id)
            return

        # ========== EXISTING FLOWS (LEGACY SUPPORT) ==========
        if data == "log_photo":
            await query.edit_message_text(
                "📷 Please upload a photo of your skin. Make sure it's well-lit and clear!"
            )
            return
        elif data == "log_product":
            await self._show_product_options(query)
            return
        elif data == "log_trigger":
            context.user_data["selected_triggers"] = []
            await self._show_trigger_options(query, context)
            return
        elif data == "log_symptom":
            context.user_data["selected_symptoms"] = []
            await self._show_symptom_options(query, context)
            return

        if data == "settings_add_condition":
            context.user_data["awaiting_condition_name"] = True
            await query.edit_message_text("Please enter the condition name:")
            return

        if data == "settings_reminder":
            # Show reminder time options
            await self._show_reminder_settings(query, context)
            return

        if data == "settings_products":
            # Show product management options
            await self._show_product_management(query, context, user_id)
            return

        if data == "settings_delete_data":
            # Show data deletion options
            await self._show_delete_data_options(query, context, user_id)
            return

        if data.startswith("condition_type_"):
            condition_type = data.replace("condition_type_", "")
            name = context.user_data.get("new_condition_name")
            if name:
                await self.database.add_condition(user_id, name, condition_type)
                await query.edit_message_text(
                    f"✅ Condition added: {name} ({condition_type})"
                )
                context.user_data.pop("new_condition_name", None)
                context.user_data.pop("awaiting_condition_type", None)
                await self._show_settings(update, context)
            else:
                await query.edit_message_text("Condition name missing.")
            return

        if data.startswith("product_"):
            product_name = data.replace("product_", "").replace("_", " ")
            if product_name == "Other":
                context.user_data["awaiting_custom_product"] = True
                await query.edit_message_text("Please type your custom product:")
            else:
                await self._log_product(query, user_id, product_name)
                await self.send_main_menu(update)
            return

        if data.startswith("trigger_toggle_"):
            key = data.replace("trigger_toggle_", "")
            available = context.user_data.get("available_triggers", [])
            trigger = next((t for t in available if t.lower().replace(' ', '_') == key), key.replace('_', ' '))
            if trigger == "Other":
                context.user_data["awaiting_custom_trigger"] = True
                await query.edit_message_text("Please type your custom trigger:")
            else:
                selected = context.user_data.setdefault("selected_triggers", [])
                if trigger in selected:
                    selected.remove(trigger)
                else:
                    selected.append(trigger)
                await self._show_trigger_options(query, context)
            return
        elif data == "trigger_submit":
            selected = context.user_data.get("selected_triggers", [])
            if selected:
                for t in selected:
                    await self.database.log_trigger(user_id, t)
                context.user_data["selected_triggers"] = []
                await query.edit_message_text(f"✅ Logged triggers: {', '.join(selected)}")
                await self.send_main_menu(update)
            else:
                await query.answer("No triggers selected", show_alert=True)
            return

        if data.startswith("symptom_toggle_"):
            key = data.replace("symptom_toggle_", "")
            symptom = next((s for s in self.symptoms if s.lower().replace(' ', '_') == key), key.replace('_', ' '))
            if symptom == "Other":
                context.user_data["awaiting_custom_symptom"] = True
                await query.edit_message_text("Please type your custom symptom:")
            else:
                selected = context.user_data.setdefault("selected_symptoms", [])
                if symptom in selected:
                    selected.remove(symptom)
                else:
                    selected.append(symptom)
                await self._show_symptom_options(query, context)
            return
        elif data == "symptom_submit":
            selected = context.user_data.get("selected_symptoms", [])
            if selected:
                context.user_data['symptoms_pending_severity'] = selected
                context.user_data['awaiting_severity'] = True
                await query.edit_message_text("Please rate severity (1-5):")
            else:
                await query.answer("No symptoms selected", show_alert=True)
            return

        if data.startswith("reminder_"):
            time_str = data.split("_", 1)[1]
            await self.database.update_user_reminder(user_id, time_str)
            if self.scheduler:
                self.scheduler.schedule_daily_reminder(user_id, time_str)
            await query.edit_message_text(
                f"✅ Daily reminder set for {time_str}",
            )
            return

        if data.startswith("mood_rate_"):
            # Handle daily mood rating from check-in
            rating_num = int(data.split("_", 2)[2])
            rating_map = {
                5: "Excellent",
                4: "Good", 
                3: "Okay",
                2: "Bad",
                1: "Very Bad"
            }
            
            mood_description = rating_map.get(rating_num, "Unknown")
            
            # Log the mood rating
            success = await self.database.log_daily_mood(user_id, rating_num, mood_description)
            
            if success:
                emoji_map = {
                    5: "✅",
                    4: "🟢", 
                    3: "🟡",
                    2: "🟠",
                    1: "🔴"
                }
                emoji = emoji_map.get(rating_num, "")
                
                await query.edit_message_text(
                    f"✅ *Mood Logged!*\n\n"
                    f"Today's skin feeling: {emoji} {mood_description}\n\n"
                    f"Thanks for checking in! Continue with your daily log?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Continue Check-in", callback_data="daily_checkin")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="show_main_menu")]
                    ])
                )
            else:
                await query.edit_message_text(
                    "❌ Sorry, there was an error logging your mood. Please try again later."
                )
            return

        if data.startswith("rating_"):
            # Handle daily mood rating from reminder
            rating_num = int(data.split("_", 1)[1])
            rating_map = {
                5: "Excellent",
                4: "Good", 
                3: "Okay",
                2: "Bad",
                1: "Flare-up"
            }
            
            mood_description = rating_map.get(rating_num, "Unknown")
            
            # Log the mood rating
            success = await self.database.log_daily_mood(user_id, rating_num, mood_description)
            
            if success:
                emoji_map = {
                    5: "😃",
                    4: "🙂", 
                    3: "😐",
                    2: "😕",
                    1: "😫"
                }
                emoji = emoji_map.get(rating_num, "")
                
                await query.edit_message_text(
                    f"✅ Thanks for sharing! Logged: {emoji} {mood_description}\n\n"
                    f"Take care of your skin today! 💚"
                )
            else:
                await query.edit_message_text(
                    "❌ Sorry, there was an error logging your mood. Please try again later."
                )
            return

        # Settings handlers
        if data == "settings_back":
            await self._show_settings(update, context)
            return

        if data.startswith("set_reminder_"):
            time_or_action = data.replace("set_reminder_", "")
            if time_or_action == "disable":
                # Disable reminders
                if self.scheduler:
                    self.scheduler.remove_reminder(user_id)
                await self.database.update_user_reminder(user_id, None)
                await query.edit_message_text("✅ Daily reminders disabled.")
            else:
                # Set new reminder time
                await self.database.update_user_reminder(user_id, time_or_action)
                if self.scheduler:
                    self.scheduler.schedule_daily_reminder(user_id, time_or_action)
                
                # Check if this is from onboarding
                user = await self.database.get_user_by_telegram_id(user_id)
                is_onboarding = not user.get('onboarding_completed', False) if user else True
                
                if is_onboarding:
                    await query.edit_message_text(
                        f"✅ *Perfect!*\n\n"
                        f"You'll get a daily reminder at {time_or_action} to check in with your skin.\n\n"
                        f"Next, let's set up your tracking areas...",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("➡️ Continue Setup", callback_data="onboarding_areas")]
                        ])
                    )
                else:
                    await query.edit_message_text(f"✅ Daily reminder set for {time_or_action}")
                    # Return to settings after 2 seconds
                    await asyncio.sleep(2)
                    await self._show_settings(update, context)
            return

        if data.startswith("edit_product_"):
            product_name = data.replace("edit_product_", "").replace("_", " ")
            context.user_data["editing_product"] = product_name
            keyboard = [
                [InlineKeyboardButton("✏️ Rename", callback_data=f"rename_product_{product_name.replace(' ', '_')}")],
                [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_product_{product_name.replace(' ', '_')}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="settings_products")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"🏷️ *Product: {product_name}*\n\nWhat would you like to do?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return

        if data.startswith("rename_product_"):
            product_name = data.replace("rename_product_", "").replace("_", " ")
            context.user_data["renaming_product"] = product_name
            context.user_data["awaiting_new_product_name"] = True
            await query.edit_message_text(f"✏️ Enter new name for '{product_name}':")
            return

        if data.startswith("delete_product_"):
            product_name = data.replace("delete_product_", "").replace("_", " ")
            success = await self.database.delete_product(user_id, product_name)
            if success:
                await query.edit_message_text(f"✅ Product '{product_name}' deleted.")
            else:
                await query.edit_message_text(f"❌ Failed to delete '{product_name}'.")
            
            await asyncio.sleep(2)
            await self._show_product_management(query, context, user_id)
            return

        if data.startswith("delete_data_"):
            data_type = data.replace("delete_data_", "")
            
            if data_type == "photos":
                types_to_delete = ["photos", "kpis"]
                confirmation_text = "📸 Delete all photos and skin analysis data?"
            elif data_type == "logs":
                types_to_delete = ["products", "triggers", "symptoms", "moods"]
                confirmation_text = "📝 Delete all logging data (products, triggers, symptoms, moods)?"
            elif data_type == "all":
                types_to_delete = ["photos", "products", "triggers", "symptoms", "moods", "kpis"]
                confirmation_text = "🗑️ Delete ALL data? This cannot be undone!"
            else:
                return

            # Show confirmation
            keyboard = [
                [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{data_type}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="settings_delete_data")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"⚠️ *Confirmation Required*\n\n{confirmation_text}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return

        if data.startswith("confirm_delete_"):
            data_type = data.replace("confirm_delete_", "")
            
            # Determine what to delete
            if data_type == "photos":
                types_to_delete = ["photos", "kpis"]
            elif data_type == "logs":
                types_to_delete = ["products", "triggers", "symptoms", "moods"]
            elif data_type == "all":
                types_to_delete = ["photos", "products", "triggers", "symptoms", "moods", "kpis"]
            else:
                return

            # Perform deletion
            results = await self.database.delete_all_user_data(user_id, types_to_delete)
            
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            if success_count == total_count:
                await query.edit_message_text("✅ Data deleted successfully!")
            else:
                await query.edit_message_text(f"⚠️ Partial success: {success_count}/{total_count} deletions completed.")
            
            await asyncio.sleep(2)
            await self._show_settings(update, context)
            return

    def _reminder_time_keyboard(self) -> InlineKeyboardMarkup:
        """Build keyboard with common reminder time options."""
        times = ["09:00", "12:00", "18:00"]
        keyboard = [[InlineKeyboardButton(t, callback_data=f"reminder_{t}")] for t in times]
        return InlineKeyboardMarkup(keyboard)

    async def _show_product_options(self, query):
        """Show product selection keyboard."""
        user_id = query.from_user.id
        products = await self.database.get_products(user_id)
        names = [p['name'] for p in products] if products else self.default_products
        if "Other" not in names:
            names.append("Other")
        keyboard = []
        for i in range(0, len(names), 2):
            row = []
            row.append(
                InlineKeyboardButton(
                    names[i],
                    callback_data=f"product_{names[i].replace(' ', '_')}"
                )
            )
            if i + 1 < len(names):
                row.append(
                    InlineKeyboardButton(
                        names[i + 1],
                        callback_data=f"product_{names[i + 1].replace(' ', '_')}"
                    )
                )
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🧴 Which product did you use?",
            reply_markup=reply_markup
        )

    async def _show_trigger_options(self, query, context):
        """Show trigger selection keyboard with multi-select."""
        user_id = query.from_user.id
        triggers = await self.database.get_triggers(user_id)
        names = [t['name'] for t in triggers] if triggers else self.default_triggers
        if "Other" not in names:
            names.append("Other")
        context.user_data['available_triggers'] = names
        selected = context.user_data.get("selected_triggers", [])
        keyboard = []
        for trigger in names:
            if trigger == "Other":
                keyboard.append([
                    InlineKeyboardButton("Other", callback_data="trigger_toggle_other")
                ])
            else:
                prefix = "✅ " if trigger in selected else ""
                keyboard.append([
                    InlineKeyboardButton(
                        f"{prefix}{trigger}",
                        callback_data=f"trigger_toggle_{trigger.lower().replace(' ', '_')}",
                    )
                ])

        keyboard.append([InlineKeyboardButton("✅ Submit", callback_data="trigger_submit")])

        await query.edit_message_text(
            "⚡ Select triggers and tap Submit:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def _show_symptom_options(self, query, context):
        """Show symptom selection keyboard with multi-select."""
        selected = context.user_data.get("selected_symptoms", [])
        keyboard = []
        for symptom in self.symptoms:
            if symptom == "Other":
                keyboard.append([
                    InlineKeyboardButton("Other", callback_data="symptom_toggle_other")
                ])
            else:
                prefix = "✅ " if symptom in selected else ""
                keyboard.append([
                    InlineKeyboardButton(
                        f"{prefix}{symptom}",
                        callback_data=f"symptom_toggle_{symptom.lower().replace(' ', '_')}",
                    )
                ])

        keyboard.append([InlineKeyboardButton("✅ Submit", callback_data="symptom_submit")])

        await query.edit_message_text(
            "📊 Select symptoms and tap Submit:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def _log_product(self, query, user_id: int, product_name: str):
        """Log a product usage."""
        try:
            await self.database.log_product(user_id, product_name)
            await query.edit_message_text(
                f"✅ Logged product: {product_name}\n\n"
                "Use /log to record more or /summary for insights!"
            )
        except Exception as e:
            logger.exception("Error logging product")
            await query.edit_message_text("Sorry, there was an error logging your product.")

    async def _log_trigger(self, query, user_id: int, trigger_name: str):
        """Log a trigger."""
        try:
            await self.database.log_trigger(user_id, trigger_name)
            await query.edit_message_text(
                f"✅ Logged trigger: {trigger_name}\n\n"
                "Use /log to record more or /summary for insights!"
            )
        except Exception as e:
            logger.exception("Error logging trigger")
            await query.edit_message_text("Sorry, there was an error logging your trigger.")

    async def handle_photo(self, update: Update, context):
        user_id = update.effective_user.id
        photo = update.message.photo[-1]

        try:
            logger.info(f"[Photo] Starting photo handling for user {user_id}")
            file = await context.bot.get_file(photo.file_id)
            logger.info(f"[Photo] Got file info for user {user_id}, file_id: {photo.file_id}")
            
            photo_url, temp_path, image_id = await self.database.save_photo(user_id, file)
            logger.info(f"[Photo] Saved photo for user {user_id}: url={photo_url}, temp_path={temp_path}, image_id={image_id}")

            async def process_and_cleanup():
                try:
                    logger.info(f"[Photo] Starting background analysis for user {user_id}, image_id={image_id}")
                    # If process_skin_image takes (path, user_id, image_id, client, analysis_provider)
                    await asyncio.to_thread(
                        process_skin_image,
                        temp_path,
                        str(user_id),
                        image_id,
                        self.database.client,
                        self.analysis_provider,   # ← remove this arg if not in the signature
                    )
                    logger.info(f"[Photo] Background analysis completed for user {user_id}, image_id={image_id}")
                except Exception:
                    logger.exception("process_skin_image failed for image_id=%s", image_id)
                finally:
                    try:
                        os.unlink(temp_path)
                        logger.info("Temp file deleted: %s", temp_path)
                    except Exception as cleanup_error:
                        logger.warning("Could not delete temp file %s: %s", temp_path, cleanup_error)

            # Kick off the background work (no extra parentheses)
            asyncio.create_task(process_and_cleanup())

            logger.info(f"[Photo] Logging photo to database for user {user_id}")
            await self.database.log_photo(user_id, photo_url)
            logger.info(f"[Photo] Successfully logged photo for user {user_id}")
            
            await update.message.reply_text("📷 Photo uploaded successfully!")
            await self.send_main_menu(update)
            logger.info(f"[Photo] Completed photo handling for user {user_id}")

        except Exception:
            logger.exception("Error handling photo")
            await update.message.reply_text(
                "Sorry, there was an error processing your photo. Please try again."
            )
            await self.send_main_menu(update)

    async def handle_text(self, update: Update, context):
        """Handle plain text messages for custom trigger/symptom inputs."""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        if context.user_data.get("awaiting_severity"):
            try:
                severity = int(text)
                if severity < 1 or severity > 5:
                    raise ValueError
                symptoms = context.user_data.get('symptoms_pending_severity', [])
                for s in symptoms:
                    await self.database.log_symptom(user_id, s, severity)
                context.user_data.pop('awaiting_severity', None)
                context.user_data.pop('symptoms_pending_severity', None)
                context.user_data['selected_symptoms'] = []
                await update.message.reply_text(
                    f"✅ Logged symptoms: {', '.join(symptoms)} (severity {severity})"
                )
                await self.send_main_menu(update)
            except ValueError:
                await update.message.reply_text("Please enter a number between 1 and 5 for severity.")
        elif context.user_data.get("awaiting_custom_product"):
            await self.database.add_product(user_id, text)
            await self.database.log_product(user_id, text)
            del context.user_data["awaiting_custom_product"]
            await update.message.reply_text(f"✅ Logged product: {text}")
            await self.send_main_menu(update)
        elif context.user_data.get("awaiting_custom_trigger"):
            await self.database.add_trigger(user_id, text)
            await self.database.log_trigger(user_id, text)
            del context.user_data["awaiting_custom_trigger"]
            await update.message.reply_text(f"✅ Logged trigger: {text}")
            await self.send_main_menu(update)
        elif context.user_data.get("awaiting_custom_symptom"):
            context.user_data['symptoms_pending_severity'] = [text]
            context.user_data['awaiting_severity'] = True
            del context.user_data["awaiting_custom_symptom"]
            await update.message.reply_text("Please rate severity (1-5):")
        elif context.user_data.get("awaiting_condition_name"):
            context.user_data["new_condition_name"] = text
            context.user_data.pop("awaiting_condition_name", None)
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Existing", callback_data="condition_type_existing"
                    ),
                    InlineKeyboardButton(
                        "Developed", callback_data="condition_type_developed"
                    ),
                ]
            ]
            await update.message.reply_text(
                "Is this condition existing or developed?",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            context.user_data["awaiting_condition_type"] = True
        elif context.user_data.get("awaiting_new_product_name"):
            # Handle product renaming
            old_name = context.user_data.get("renaming_product")
            new_name = text.strip()
            
            if old_name and new_name:
                success = await self.database.update_product_name(user_id, old_name, new_name)
                if success:
                    await update.message.reply_text(f"✅ Product renamed: '{old_name}' → '{new_name}'")
                else:
                    await update.message.reply_text(f"❌ Failed to rename product '{old_name}'")
            else:
                await update.message.reply_text("❌ Invalid product name")
            
            # Clean up and return to product management
            context.user_data.pop("awaiting_new_product_name", None)
            context.user_data.pop("renaming_product", None)
            
            # Show updated product list after a short delay
            await asyncio.sleep(1)
            # Create a fake query object to reuse the existing method
            class FakeQuery:
                def __init__(self, message):
                    self.message = message
                
                async def edit_message_text(self, text, parse_mode=None, reply_markup=None):
                    await self.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            
            fake_query = FakeQuery(update.message)
            await self._show_product_management(fake_query, context, user_id)
        else:
            await update.message.reply_text("I'm not sure what you mean. Use /help to see available commands!")

    # Timeline and Quick Logging Commands
    
    async def timeline_command(self, update: Update, context):
        """Handle /timeline command - show timeline web app."""
        try:
            # Create timeline web app URL with user ID
            base_url = os.getenv('BASE_URL', 'https://rstrinati.github.io/SkinTracker')
            user_id = update.effective_user.id
            
            # Create different URLs for different hosting scenarios
            timeline_urls = {
                'webapp': f"{base_url}/timeline?user_id={user_id}",
                'github': f"https://rstrinati.github.io/SkinTracker/timeline-standalone.html?user_id={user_id}",
                'browser': f"{base_url}/timeline?user_id={user_id}&mode=browser"
            }
            
            # Create inline keyboard with Web App button
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
            
            keyboard = [
                [InlineKeyboardButton("📈 Open Timeline (WebApp)", web_app=WebAppInfo(url=timeline_urls['webapp']))],
                [InlineKeyboardButton("🌐 Open Timeline (GitHub Pages)", url=timeline_urls['github'])],
                [InlineKeyboardButton("🔗 Open in Browser", url=timeline_urls['browser'])]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📈 *Your Skin Health Timeline*\n\n"
                "View your complete skin health journey with:\n"
                "• 📊 All symptoms, triggers, and treatments\n"
                "• 🔍 AI insights on what's working\n"
                "• 📈 Trends and patterns over time\n"
                "• 📷 Photo timeline with analysis\n\n"
                "Choose how to open your timeline:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in timeline command: {e}")
            await update.message.reply_text("❌ Error opening timeline. Please try again later.")

    async def quick_trigger_command(self, update: Update, context):
        """Handle /trigger command for quick trigger logging."""
        try:
            user_id = update.effective_user.id
            
            # Parse command arguments
            if context.args:
                trigger_text = " ".join(context.args)
                parts = trigger_text.split(' note:"')
                trigger_name = parts[0].strip()
                notes = parts[1].rstrip('"') if len(parts) > 1 else None
                
                # Log the trigger
                await self.database.log_trigger(user_id, trigger_name, notes)
                
                response = f"✅ Trigger logged: *{trigger_name}*"
                if notes:
                    response += f"\nNote: _{notes}_"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    "🎯 *Quick Trigger Logging*\n\n"
                    "Usage: `/trigger <trigger_name> note:\"<optional_note>\"`\n\n"
                    "Examples:\n"
                    "• `/trigger Sun exposure`\n"
                    "• `/trigger Stress note:\"work deadline\"`\n"
                    "• `/trigger Spicy food note:\"Thai restaurant\"`",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in quick trigger command: {e}")
            await update.message.reply_text("❌ Error logging trigger. Please try again.")

    async def quick_symptom_command(self, update: Update, context):
        """Handle /symptom command for quick symptom logging."""
        try:
            user_id = update.effective_user.id
            
            # Parse command arguments
            if len(context.args) >= 2:
                symptom_name = context.args[0]
                try:
                    severity = int(context.args[1])
                    if severity < 1 or severity > 5:
                        raise ValueError("Severity must be 1-5")
                except ValueError:
                    await update.message.reply_text(
                        "❌ Invalid severity. Please use a number from 1 (mild) to 5 (severe)."
                    )
                    return
                
                # Check for notes
                notes = None
                if len(context.args) > 2:
                    remaining_args = " ".join(context.args[2:])
                    if remaining_args.startswith('note:"') and remaining_args.endswith('"'):
                        notes = remaining_args[6:-1]  # Remove note:" and closing "
                
                # Log the symptom
                await self.database.log_symptom(user_id, symptom_name, severity, notes)
                
                severity_emoji = ["", "😐", "😕", "😖", "😣", "😫"][severity]
                response = f"✅ Symptom logged: *{symptom_name}* {severity_emoji} (Severity: {severity}/5)"
                if notes:
                    response += f"\nNote: _{notes}_"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    "🔥 *Quick Symptom Logging*\n\n"
                    "Usage: `/symptom <name> <severity> note:\"<optional_note>\"`\n\n"
                    "Severity Scale:\n"
                    "• 1 😐 - Very mild\n"
                    "• 2 😕 - Mild\n"
                    "• 3 😖 - Moderate\n"
                    "• 4 😣 - Severe\n"
                    "• 5 😫 - Very severe\n\n"
                    "Examples:\n"
                    "• `/symptom Redness 3`\n"
                    "• `/symptom Itching 4 note:\"couldn't sleep\"`",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in quick symptom command: {e}")
            await update.message.reply_text("❌ Error logging symptom. Please try again.")

    async def quick_product_command(self, update: Update, context):
        """Handle /product command for quick product logging."""
        try:
            user_id = update.effective_user.id
            
            # Parse command arguments
            if context.args:
                product_text = " ".join(context.args)
                parts = product_text.split(' note:"')
                product_name = parts[0].strip()
                notes = parts[1].rstrip('"') if len(parts) > 1 else None
                
                # Log the product (effect defaults to "Applied")
                await self.database.log_product(user_id, product_name, effect="Applied", notes=notes)
                
                response = f"✅ Product logged: *{product_name}*"
                if notes:
                    response += f"\nNote: _{notes}_"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    "💊 *Quick Product Logging*\n\n"
                    "Usage: `/product <product_name> note:\"<optional_note>\"`\n\n"
                    "Examples:\n"
                    "• `/product Soolantra`\n"
                    "• `/product Moisturizer note:\"evening routine\"`\n"
                    "• `/product Sunscreen note:\"SPF 50\"`",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in quick product command: {e}")
            await update.message.reply_text("❌ Error logging product. Please try again.")

    # ========== NEW UX ENHANCEMENT METHODS ==========

    async def _handle_checkin_actions(self, query, context):
        """Handle specific check-in actions."""
        data = query.data
        user_id = query.from_user.id
        
        if data == "checkin_photo":
            await query.edit_message_text(
                "📸 *Daily Photo Check-in*\n\n"
                "Upload today's skin photo:\n\n"
                "*💡 For best results:*\n"
                "• Use the same lighting as previous photos\n"
                "• Keep the same distance and angle\n"
                "• Clean skin, no makeup\n\n"
                "Upload your photo now! 📷",
                parse_mode=ParseMode.MARKDOWN
            )
            
        elif data == "checkin_mood":
            await self._show_mood_rating(query, context)
            
        elif data == "checkin_symptoms":
            context.user_data["selected_symptoms"] = []
            await self._show_symptom_options(query, context)
            
        elif data == "checkin_products":
            await self._show_product_options(query)
            
        elif data == "checkin_triggers":
            context.user_data["selected_triggers"] = []
            await self._show_trigger_options(query, context)

    async def _show_mood_rating(self, query, context):
        """Show mood/skin feeling rating for daily check-in."""
        text = """😊 *How is your skin feeling today?*

Rate your overall skin condition on a scale of 1-5:

🔴 **1** - Very bad (painful, severely inflamed)
🟠 **2** - Bad (uncomfortable, noticeable issues)  
🟡 **3** - Okay (some issues, manageable)
🟢 **4** - Good (minor issues, mostly clear)
✅ **5** - Excellent (clear, comfortable, confident)

*This helps track your daily progress and identify patterns!*"""

        keyboard = [
            [
                InlineKeyboardButton("🔴 1", callback_data="mood_rate_1"),
                InlineKeyboardButton("🟠 2", callback_data="mood_rate_2"),
                InlineKeyboardButton("🟡 3", callback_data="mood_rate_3"),
                InlineKeyboardButton("🟢 4", callback_data="mood_rate_4"),
                InlineKeyboardButton("✅ 5", callback_data="mood_rate_5")
            ],
            [InlineKeyboardButton("⬅️ Back to Check-in", callback_data="daily_checkin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def _show_area_details(self, query, context, user_id, area_name):
        """Show detailed progress for a specific area."""
        # Get area-specific data
        area_logs = await self.database.get_area_logs(user_id, area_name, days=30)
        area_photos = await self.database.get_area_photos(user_id, area_name, days=30)
        
        text = f"📊 *{area_name} - Detailed Progress*\n\n"
        
        if not area_logs and not area_photos:
            text += "No recent activity for this area.\n\n"
            text += "*Start logging symptoms and uploading photos to track progress!*"
        else:
            # Show recent activity summary
            text += f"📈 **Last 30 Days:**\n"
            text += f"• Symptom logs: {len(area_logs)}\n"
            text += f"• Photos: {len(area_photos)}\n\n"
            
            # Show recent symptoms if any
            if area_logs:
                recent_symptoms = {}
                for log in area_logs[-5:]:  # Last 5 logs
                    symptom = log['symptom_name']
                    severity = log['severity']
                    recent_symptoms[symptom] = recent_symptoms.get(symptom, []) + [severity]
                
                text += "🔍 **Recent Symptoms:**\n"
                for symptom, severities in recent_symptoms.items():
                    avg_severity = sum(severities) / len(severities)
                    text += f"• {symptom}: {avg_severity:.1f}/5 avg\n"
                text += "\n"
            
            text += "*💡 Tip:* Keep logging to see improvement trends and get personalized recommendations!"

        keyboard = [
            [InlineKeyboardButton("📝 Log for this Area", callback_data=f"area_log_{area_name.replace(' ', '_')}")],
            [InlineKeyboardButton("⬅️ Back to Areas", callback_data="area_management")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

