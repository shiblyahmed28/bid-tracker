from celery import shared_task

from apps.sync.models import SyncRun
from apps.sync.sync import run_sync


@shared_task
def sync_sheet_task():
    sync_run, counts = run_sync(trigger=SyncRun.Trigger.SCHEDULED)
    return counts
