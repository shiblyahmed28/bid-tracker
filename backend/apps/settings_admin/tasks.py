from celery import shared_task

from .services import send_deadline_reminders


@shared_task
def send_deadline_reminders_task():
    """Daily Beat task at 08:00 Asia/Dhaka — replaces the old hard-coded
    7-day-only task (apps.notifications.tasks.send_deadline_alerts_task,
    left in place but no longer scheduled) with one that loops every active
    DeadlineReminderRule and dedupes per bid per rule (§Phase 15C)."""
    return send_deadline_reminders()
