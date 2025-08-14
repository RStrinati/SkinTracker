from __future__ import annotations

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from types import SimpleNamespace
import logging

try:  # pragma: no cover - used when APScheduler is available
    from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without APScheduler
    class AsyncIOScheduler:  # minimal stub for tests
        """Very small subset of :class:`AsyncIOScheduler` used in tests.

        This stub only stores jobs so tests can verify that a reminder was
        scheduled without requiring the external APScheduler dependency.
        """

        def __init__(self, timezone: str = "UTC"):
            self.jobs = {}

        def start(self) -> None:
            pass

        def add_job(
            self,
            func,
            trigger,
            hour,
            minute,
            args=None,
            timezone: str | None = None,
            id: str | None = None,
            replace_existing: bool = False,
        ) -> None:
            self.jobs[id] = SimpleNamespace(func=func, args=args, id=id)

        def get_job(self, job_id: str):
            return self.jobs.get(job_id)

        def remove_job(self, job_id: str) -> None:
            if job_id in self.jobs:
                del self.jobs[job_id]

        def shutdown(self, wait: bool = False) -> None:
            self.jobs.clear()


class ReminderScheduler:
    """Schedule daily check-in reminders for users.

    The scheduler uses APScheduler's :class:`AsyncIOScheduler` so that it
    can run in the same asyncio event loop as ``python-telegram-bot``.
    Each job is identified by ``reminder_<chat_id>`` which allows
    replacing existing jobs when a user updates their reminder time.
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.scheduler.start()
        self.logger = logging.getLogger(__name__)

    def schedule_daily_reminder(self, chat_id: int, reminder_time: str, timezone: str = "UTC") -> None:
        """Schedule or reschedule a user's daily reminder.

        Parameters
        ----------
        chat_id: int
            Telegram chat identifier where the reminder will be sent.
        reminder_time: str
            Time in ``HH:MM`` format.
        timezone: str
            IANA timezone string, defaults to ``UTC``.
        """
        hour, minute = map(int, reminder_time.split(":"))
        self.scheduler.add_job(
            self.send_daily_reminder,
            "cron",
            hour=hour,
            minute=minute,
            args=[chat_id],
            timezone=timezone,
            id=f"reminder_{chat_id}",
            replace_existing=True,
        )
        self.logger.info(
            "Scheduled daily reminder for chat %s at %s (%s)",
            chat_id,
            reminder_time,
            timezone,
        )

    async def send_daily_reminder(self, chat_id: int) -> None:
        """Send the daily reminder message with rating buttons."""
        keyboard = [
            [
                InlineKeyboardButton("😃 Excellent", callback_data="rating_5"),
                InlineKeyboardButton("🙂 Good", callback_data="rating_4"),
            ],
            [
                InlineKeyboardButton("😐 Okay", callback_data="rating_3"),
                InlineKeyboardButton("😕 Bad", callback_data="rating_2"),
            ],
            [
                InlineKeyboardButton("😫 Flare-up", callback_data="rating_1"),
            ],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await self.bot.send_message(chat_id, "How does your skin feel today?", reply_markup=markup)

    def remove_reminder(self, chat_id: int) -> None:
        """Remove a user's daily reminder.

        Parameters
        ----------
        chat_id: int
            Telegram chat identifier of the reminder to remove.
        """
        job_id = f"reminder_{chat_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            self.logger.info("Removed daily reminder for chat %s", chat_id)

    def shutdown(self) -> None:
        """Shutdown the underlying APScheduler instance."""
        self.scheduler.shutdown(wait=False)
