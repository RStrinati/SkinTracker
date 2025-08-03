import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import traceback

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

from database import Database
from openai_service import OpenAIService

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
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
        
        # Predefined options for logging
        self.products = [
            "Cicaplast", "Azelaic Acid", "Enstilar", "Cerave Moisturizer", 
            "Sunscreen", "Retinol", "Niacinamide", "Salicylic Acid", "Other"
        ]
        
        # Updated predefined options for triggers and symptoms
        self.triggers = [
            "Sun exposure",
            "Stress",
            "Hot weather",
            "Sweating",
            "Spicy food",
            "Alcohol",
            "Other",
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
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
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
            BotCommand("progress", "📊 View progress"),
            BotCommand("settings", "⚙️ Settings"),
        ]
        await self.bot.set_my_commands(commands)
        await self.bot.set_chat_menu_button()

    async def initialize(self):
        """Initialize the bot and database."""
        await self.database.initialize()
        await self.application.initialize()  # 👈 REQUIRED
        await self.application.start()       # 👈 REQUIRED
        self.bot = self.application.bot  # Make sure this is after `initialize()`
        await self._setup_persistent_menu()
        logger.info("Bot initialized successfully")

    async def shutdown(self):
        """Cleanup resources."""
        await self.application.stop()
        await self.application.shutdown()
        await self.database.close()
        logger.info("Bot shut down successfully")

    async def send_main_menu(self, update: Update):
        """Send persistent main menu buttons."""
        keyboard = [
            [
                InlineKeyboardButton("📝 Log", callback_data="menu_log"),
                InlineKeyboardButton("📊 Progress", callback_data="menu_progress"),
                InlineKeyboardButton("🧠 Summary", callback_data="menu_summary"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = update.message or update.callback_query.message
        await message.reply_text("Main Menu", reply_markup=reply_markup)


    async def process_update(self, update_data: dict):
        """Process incoming Telegram update."""
        try:
            update = Update.de_json(update_data, self.bot)
            await self.application.process_update(update)
        except Exception as e:
            logger.error(f"Error processing update: {e}")

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
        """Handle /start command - register user."""
        user = update.effective_user
        telegram_id = user.id
        
        try:
            # Register user in database
            await self.database.create_user(
                telegram_id=telegram_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            welcome_message = f"""
🌟 *Welcome to Skin Health Tracker!* 🌟

Hi {user.first_name}! I'm here to help you track your skin health journey.

*What I can help you with?:*
📷 Upload skin photos for progress tracking
🧴 Log skincare products you're using
⚡ Track triggers that affect your skin
📊 Rate symptom severity (1-5 scale)
📈 Get AI-powered insights and summaries

*Available commands:*
/log - Start logging (photos, products, triggers, symptoms)
/summary - Get your weekly progress summary
/help - Learn more about logging options

Ready to start your skin health journey? Use /log to begin! ✨
            """
            
            await update.message.reply_text(
                welcome_message,
                parse_mode=ParseMode.MARKDOWN
            )

            await self.send_main_menu(update)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            traceback.print_exc()
            await update.message.reply_text(
                "Sorry, there was an error registering you. Please try again."
            )
            await self.send_main_menu(update)

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
            logger.error(f"Error generating summary: {e}")
            message = update.message or update.callback_query.message
            await message.reply_text(
                "Sorry, I couldn't generate your summary right now. Please try again later."
            )
            await self.send_main_menu(update)

    async def progress_command(self, update: Update, context):
        """Handle /progress command - show user statistics."""
        user_id = update.effective_user.id
        try:
            stats = await self.database.get_user_stats(user_id, days=30)
            text = (
                "📊 *30-day Overview*\n"
                f"• Products logged: {stats.get('product_count', 0)}\n"
                f"• Triggers logged: {stats.get('trigger_count', 0)}\n"
                f"• Symptoms logged: {stats.get('symptom_count', 0)}\n"
                f"• Photos uploaded: {stats.get('photo_count', 0)}"
            )
            message = update.message or update.callback_query.message
            await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            await self.send_main_menu(update)
        except Exception as e:
            logger.error(f"Error getting progress: {e}")
            message = update.message or update.callback_query.message
            await message.reply_text("Sorry, I couldn't load your progress right now.")
            await self.send_main_menu(update)

    async def settings_command(self, update: Update, context):
        """Handle /settings command - show placeholder settings."""
        keyboard = [[InlineKeyboardButton("➕ Add Condition", callback_data="settings_add_condition")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚙️ Settings coming soon! Manage your conditions and preferences here.",
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context):
        """Handle /help command - show help information."""
        help_text = """
📚 *Skin Health Tracker Help*

*Logging Types:*

📷 **Photos**: Upload pictures of your skin for visual progress tracking
• Best taken in consistent lighting
• Same angle and distance when possible
• AI will analyze changes over time

🧴 **Products**: Log skincare products you use
• Track what works for your skin
• Identify beneficial vs. problematic products
• Build your personal skincare profile

⚡ **Triggers**: Record factors that affect your skin
• Environmental (sun, weather, pollution)
• Lifestyle (stress, sleep, diet)
• Activities (exercise, travel)

📊 **Symptoms**: Rate severity on 1-5 scale
• 1 = Very mild, 5 = Very severe
• Track multiple symptoms at once
• Monitor improvement over time

*Commands:*
/start - Register and get started
/log - Start logging session
/summary - Get AI-powered weekly insights
/help - Show this help message

Track consistently for best results! 🌟
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def handle_callback(self, update: Update, context):
        """Handle inline keyboard button callbacks."""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id

        if data.startswith("menu_"):
            if data == "menu_log":
                await self.log_command(update, context)
            elif data == "menu_progress":
                await self.progress_command(update, context)
            elif data == "menu_summary":
                await self.summary_command(update, context)
            return

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

        if data.startswith("product_"):
            product_name = data.replace("product_", "").replace("_", " ")
            await self._log_product(query, user_id, product_name)
            await self.send_main_menu(update)
            return

        if data.startswith("trigger_toggle_"):
            key = data.replace("trigger_toggle_", "")
            trigger = next((t for t in self.triggers if t.lower().replace(' ', '_') == key), key.replace('_', ' '))
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
                for s in selected:
                    await self.database.log_symptom(user_id, s)
                context.user_data["selected_symptoms"] = []
                await query.edit_message_text(f"✅ Logged symptoms: {', '.join(selected)}")
                await self.send_main_menu(update)
            else:
                await query.answer("No symptoms selected", show_alert=True)
            return
    async def _show_product_options(self, query):
        """Show product selection keyboard."""
        keyboard = []
        for i in range(0, len(self.products), 2):
            row = []
            row.append(InlineKeyboardButton(
                self.products[i], 
                callback_data=f"product_{self.products[i].replace(' ', '_')}"
            ))
            if i + 1 < len(self.products):
                row.append(InlineKeyboardButton(
                    self.products[i + 1], 
                    callback_data=f"product_{self.products[i + 1].replace(' ', '_')}"
                ))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🧴 Which product did you use?",
            reply_markup=reply_markup
        )

    async def _show_trigger_options(self, query, context):
        """Show trigger selection keyboard with multi-select."""
        selected = context.user_data.get("selected_triggers", [])
        keyboard = []
        for trigger in self.triggers:
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
            logger.error(f"Error logging product: {e}")
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
            logger.error(f"Error logging trigger: {e}")
            await query.edit_message_text("Sorry, there was an error logging your trigger.")

    async def handle_photo(self, update: Update, context):
        """Handle photo uploads."""
        user_id = update.effective_user.id
        photo = update.message.photo[-1]  # Get highest resolution photo
        
        try:
            # Get file info
            file = await context.bot.get_file(photo.file_id)
            
            # Upload to Supabase storage and save metadata
            photo_url = await self.database.save_photo(user_id, file)
            
            # Generate AI analysis of the photo
            analysis = await self.openai_service.analyze_photo(photo_url)
            
            # Save photo log with analysis
            await self.database.log_photo(user_id, photo_url, analysis)
            
            await update.message.reply_text(
                f"📷 Photo uploaded successfully!\n\n"
                f"*AI Analysis:* {analysis}\n\n"
                "Use /log to record more or /summary for insights!",
                parse_mode=ParseMode.MARKDOWN
            )
            await self.send_main_menu(update)

        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await update.message.reply_text(
                "Sorry, there was an error processing your photo. Please try again."
            )
            await self.send_main_menu(update)

    async def handle_text(self, update: Update, context):
        """Handle plain text messages for custom trigger/symptom inputs."""
        user_id = update.effective_user.id
        text = update.message.text.strip()

        if context.user_data.get("awaiting_custom_trigger"):
            await self.database.log_trigger(user_id, text)
            del context.user_data["awaiting_custom_trigger"]
            await update.message.reply_text(f"✅ Logged trigger: {text}")
            await self.send_main_menu(update)
        elif context.user_data.get("awaiting_custom_symptom"):
            await self.database.log_symptom(user_id, text)
            del context.user_data["awaiting_custom_symptom"]
            await update.message.reply_text(f"✅ Logged symptom: {text}")
            await self.send_main_menu(update)
        else:
            await update.message.reply_text("I'm not sure what you mean. Use /help to see available commands!")

