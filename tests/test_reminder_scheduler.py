from unittest.mock import MagicMock

from reminder_scheduler import ReminderScheduler


def test_schedule_daily_reminder():
    bot = MagicMock()
    scheduler = ReminderScheduler(bot)
    scheduler.schedule_daily_reminder(chat_id=123, reminder_time="09:00", timezone="UTC")
    job = scheduler.scheduler.get_job("reminder_123")
    assert job is not None
    scheduler.shutdown()
