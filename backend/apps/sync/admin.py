from django.contrib import admin

from .models import QuarantineRow, SyncConflict, SyncRun


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "trigger",
        "status",
        "actor",
        "started_at",
        "finished_at",
        "rows_read",
        "rows_created",
        "rows_updated",
        "rows_conflicted",
        "rows_quarantined",
    )
    list_filter = ("trigger", "status")
    readonly_fields = [f.name for f in SyncRun._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(QuarantineRow)
class QuarantineRowAdmin(admin.ModelAdmin):
    list_display = ("sync_run", "sheet_row", "reason", "created_at")
    readonly_fields = [f.name for f in QuarantineRow._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    list_display = ("bid", "field", "sync_run", "resolved", "resolution", "created_at")
    list_filter = ("resolved", "resolution")
    search_fields = ("bid__reference", "field")
