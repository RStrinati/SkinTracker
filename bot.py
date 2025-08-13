import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import traceback

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

from database import Database
from openai_service import OpenAIService
from reminder_scheduler import ReminderScheduler
from analysis_providers.insightface_provider import InsightFaceProvider
from skin_analysis import process_skin_image
from services.local_storage import LocalStorageService
from services.local_summarizer import LocalAnalysisSummarizer
from services.message_queue import MessageQueueService

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
        self.analysis_provider = InsightFaceProvider()
        self.local_storage = LocalStorageService()
        self.local_summarizer = LocalAnalysisSummarizer()
        self.message_queue = MessageQueueService()

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
        await self.application.stop()
        await self.application.shutdown()
        await self.database.close()
        if self.scheduler:
            self.scheduler.shutdown()
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
            

            # Prompt user to select a reminder time
            keyboard = self._reminder_time_keyboard()
            await update.message.reply_text(
                "Select a time for your daily skin check-in:",
                reply_markup=keyboard,
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

            # Try online summary first, fallback to local if fails
            try:
                summary = await self.openai_service.generate_summary(recent_logs)
            except Exception as e:
                logger.warning(f"OpenAI summary failed, using local summarizer: {e}")
                # Extract metrics for local summarizer
                recent_photos = [log for log in recent_logs if log.get('type') == 'photo']
                if recent_photos:
                    latest = recent_photos[-1]
                    percent_blemished = latest.get('percent_blemished', 0)
                    texture_metrics = latest.get('texture_metrics', {})
                    condition_scores = latest.get('condition_scores', {})
                    summary = self.local_summarizer.generate_summary(
                        percent_blemished,
                        texture_metrics,
                        condition_scores
                    )

            # Queue message in case Telegram is down
            msg_id = self.message_queue.queue_message(
                str(update.effective_user.id),
                "summary",
                f"📈 *Your Weekly Skin Health Summary*\n\n{summary}",
            )

            try:
                await message.reply_text(
                    f"📈 *Your Weekly Skin Health Summary*\n\n{summary}",
                    parse_mode=ParseMode.MARKDOWN,
                )
                self.message_queue.mark_sent(msg_id)
            except Exception as e:
                logger.warning(f"Failed to send message, queued for later: {e}")

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

        keyboard = [[InlineKeyboardButton("➕ Add Condition", callback_data="settings_add_condition")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = update.message or update.callback_query.message
        await message.reply_text(
            f"⚙️ *Settings*\n\n*Your Conditions:*\n{condition_text}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )

    async def settings_command(self, update: Update, context):
        """Handle /settings command."""
        await self._show_settings(update, context)

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

        if data == "settings_add_condition":
            context.user_data["awaiting_condition_name"] = True
            await query.edit_message_text("Please enter the condition name:")
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

        # Send initial acknowledgment
        status_message = await update.message.reply_text(
            "📸 Receiving your photo...\n"
            "I'll analyze it and provide feedback shortly!"
        )

        try:
            # Get file info
            file = await context.bot.get_file(photo.file_id)

            # Update status
            await status_message.edit_text(
                "📸 Photo received!\n"
                "🔄 Uploading and preparing for analysis..."
            )

            try:
                # Upload to Supabase storage and get local temp path and image id
                photo_url, temp_path, image_id = await self.database.save_photo(user_id, file)
                logger.info(f"Photo saved successfully. URL: {photo_url}, Path: {temp_path}, ID: {image_id}")

                # Update status with upload confirmation
                await status_message.edit_text(
                    "📸 Photo received!\n"
                    "✅ Upload complete\n"
                    "🔍 Starting skin analysis..."
                )
            except Exception as e:
                logger.error(f"Error saving photo: {e}", exc_info=True)
                raise

            async def process_and_send_results():
                try:
                    # Process the image
                    analysis_result = await asyncio.to_thread(
                        process_skin_image,
                        temp_path,
                        str(user_id),
                        image_id,
                        self.database.client,
                        self.analysis_provider,
                    )

                    # Generate analysis summary using OpenAI
                    ai_analysis = await self.openai_service.analyze_photo(photo_url)

                    # Send the combined results
                    analysis_message = (
                        "✨ *Analysis Complete!*\n\n"
                        f"{ai_analysis}\n\n"
                        "🔍 *Technical Details:*\n"
                    )

                    if analysis_result and analysis_result.get("face_count", 0) > 0:
                        face_data = analysis_result["faces"][0]
                        percent_blemished = analysis_result.get("percent_blemished", 0)
                        analysis_message += (
                            f"• Affected Area: {percent_blemished:.1f}%\n"
                            f"• Face Area: {analysis_result.get('face_area_px', 0)} px²\n"
                            "• Analysis images have been saved for tracking\n\n"
                            "💡 Use /summary to see your progress over time!"
                        )
                    else:
                        analysis_message += (
                            "⚠️ No face detected. For best results:\n"
                            "• Ensure good lighting\n"
                            "• Face should be clearly visible\n"
                            "• Minimize glare and shadows"
                        )

                    await status_message.edit_text(
                        analysis_message,
                        parse_mode=ParseMode.MARKDOWN
                    )

                except Exception as e:
                    logger.error(f"Error in analysis: {str(e)}", exc_info=True)
                    logger.error(f"Analysis traceback: {traceback.format_exc()}")
                    await status_message.edit_text(
                        f"✅ Photo saved successfully!\n\n"
                        f"⚠️ Analysis error: {str(e)}\n\n"
                        "The photo has been saved but analysis failed.\n"
                        "This might be because:\n"
                        "• Face detection failed\n"
                        "• Image quality issues\n"
                        "• Processing error\n\n"
                        "Try taking another photo with good lighting and clear face visibility."
                    )
                finally:
                    # Cleanup
                    try:
                        os.unlink(temp_path)
                        logger.info(f"Temporary file deleted: {temp_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"Could not delete temp file: {cleanup_error}")

            # Start the analysis process in the background
            asyncio.create_task(process_and_send_results())

            # Save photo log
            await self.database.log_photo(user_id, photo_url)

            # Show the main menu
            await self.send_main_menu(update)

        except Exception as e:
            logger.error(f"Error handling photo: {e}", exc_info=True)
            logger.error(f"Full traceback: {traceback.format_exc()}")
            await status_message.edit_text(
                f"❌ Error details: {str(e)}\n\n"
                "Please try again. If the problem persists:\n"
                "• Check your internet connection\n"
                "• Try sending a smaller image\n"
                "• Wait a few minutes before trying again"
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
        else:
            await update.message.reply_text("I'm not sure what you mean. Use /help to see available commands!")

