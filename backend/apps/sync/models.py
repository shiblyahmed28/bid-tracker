from django.conf import settings
from django.db import models
from django.utils import timezone


class SyncRun(models.Model):
    class Trigger(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    trigger = models.CharField(max_length=10, choices=Trigger.choices)
    # null actor + status text alone identifies scheduled runs; audit entries
    # emitted for row changes during this run carry actor_label='System (sync)'.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="sync_runs"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    rows_read = models.PositiveIntegerField(default=0)
    rows_created = models.PositiveIntegerField(default=0)
    rows_updated = models.PositiveIntegerField(default=0)
    rows_conflicted = models.PositiveIntegerField(default=0)
    rows_quarantined = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"SyncRun #{self.pk} ({self.trigger}) — {self.status}"

    def close(self, *, status=Status.SUCCESS):
        self.status = status
        self.finished_at = timezone.now()
        self.duration_seconds = (self.finished_at - self.started_at).total_seconds()
        self.save()


class QuarantineRow(models.Model):
    sync_run = models.ForeignKey(SyncRun, on_delete=models.CASCADE, related_name="quarantined_rows")
    sheet_row = models.IntegerField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Row {self.sheet_row} quarantined: {self.reason}"


class SyncConflict(models.Model):
    class Resolution(models.TextChoices):
        SHEET = "sheet", "Sheet"
        LOCAL = "local", "Local"

    sync_run = models.ForeignKey(SyncRun, on_delete=models.CASCADE, related_name="conflicts")
    bid = models.ForeignKey("bids.Bid", on_delete=models.CASCADE, related_name="sync_conflicts")
    field = models.CharField(max_length=100)
    sheet_value = models.TextField(null=True, blank=True)
    local_value = models.TextField(null=True, blank=True)
    local_editor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    local_edited_at = models.DateTimeField(null=True, blank=True)

    resolved = models.BooleanField(default=False)
    resolution = models.CharField(max_length=10, choices=Resolution.choices, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Conflict on {self.bid.reference}.{self.field}"
