from celery import shared_task

from apps.sync.append import retry_pending_sheet_appends
from apps.sync.models import SyncRun
from apps.sync.sync import run_sync


@shared_task
def sync_sheet_task():
    sync_run, counts = run_sync(trigger=SyncRun.Trigger.SCHEDULED)
    return counts


@shared_task
def retry_pending_sheet_appends_task():
    """§Phase 23 — periodic sweep for any bid still flagged
    pending_sheet_append, independent of the read-side sync above."""
    retry_pending_sheet_appends()
