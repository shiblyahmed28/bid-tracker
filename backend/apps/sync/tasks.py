from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.sync.append import retry_pending_sheet_appends
from apps.sync.models import SyncRun
from apps.sync.sync import run_sync


@shared_task
def sync_sheet_task():
    """Celery Beat ticks this every 15 minutes (config/settings/base.py) —
    it only actually syncs once admin-configured SyncScheduleSettings'
    interval_hours have elapsed since the last scheduled run's start,
    otherwise it's a cheap no-op. This is what makes the interval editable
    from Master Settings at runtime with no container restart: the fixed
    part is how often we *check*, not how often we *sync*. Manual "Fetch
    data" triggers (SyncRunTriggerView) are a separate code path and are
    never subject to this gate."""
    from apps.settings_admin.models import SyncScheduleSettings

    interval_hours = SyncScheduleSettings.load().interval_hours
    last_run = SyncRun.objects.filter(trigger=SyncRun.Trigger.SCHEDULED).order_by("-started_at").first()
    if last_run is not None and timezone.now() - last_run.started_at < timedelta(hours=interval_hours):
        return {"skipped": True}

    sync_run, counts = run_sync(trigger=SyncRun.Trigger.SCHEDULED)
    return counts


@shared_task
def retry_pending_sheet_appends_task():
    """§Phase 23 — periodic sweep for any bid still flagged
    pending_sheet_append, independent of the read-side sync above."""
    retry_pending_sheet_appends()
