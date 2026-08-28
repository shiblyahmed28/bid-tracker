from django.core.management.base import BaseCommand

from apps.sync.models import SyncRun
from apps.sync.sync import run_sync


class Command(BaseCommand):
    help = "Sync the Google Sheet 'bids' tab into the database (§9). --dry-run reads and reports without writing anything, including no uid backfill."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Report what would change; write nothing."
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(f"Starting {'dry-run ' if dry_run else ''}sync…")
        sync_run, counts = run_sync(trigger=SyncRun.Trigger.MANUAL, dry_run=dry_run)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Dry run complete — nothing written." if dry_run else "Sync complete."))
        self.stdout.write(f"  rows read:        {counts.get('read', 0)}")
        self.stdout.write(f"  would create:     {counts.get('created', 0)}" if dry_run else f"  created:          {counts.get('created', 0)}")
        self.stdout.write(f"  would update:     {counts.get('updated', 0)}" if dry_run else f"  updated:          {counts.get('updated', 0)}")
        self.stdout.write(f"  conflicted:       {counts.get('conflicted', 0)}")
        self.stdout.write(f"  quarantined:      {counts.get('quarantined', 0)}")
        self.stdout.write(f"  duration:         {sync_run.duration_seconds:.2f}s")
