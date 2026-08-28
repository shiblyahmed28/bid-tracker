from rest_framework import serializers

from .models import QuarantineRow, SyncConflict, SyncRun


class SyncRunSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = SyncRun
        fields = [
            "id",
            "trigger",
            "actor",
            "actor_email",
            "status",
            "started_at",
            "finished_at",
            "duration_seconds",
            "rows_read",
            "rows_created",
            "rows_updated",
            "rows_conflicted",
            "rows_quarantined",
        ]
        read_only_fields = fields


class QuarantineRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuarantineRow
        fields = ["id", "sync_run", "sheet_row", "raw_data", "reason", "created_at"]
        read_only_fields = fields


class SyncConflictSerializer(serializers.ModelSerializer):
    bid_reference = serializers.CharField(source="bid.reference", read_only=True)
    local_editor_email = serializers.EmailField(source="local_editor.email", read_only=True, default=None)
    resolved_by_email = serializers.EmailField(source="resolved_by.email", read_only=True, default=None)

    class Meta:
        model = SyncConflict
        fields = [
            "id",
            "sync_run",
            "bid",
            "bid_reference",
            "field",
            "sheet_value",
            "local_value",
            "local_editor",
            "local_editor_email",
            "local_edited_at",
            "resolved",
            "resolution",
            "resolved_by",
            "resolved_by_email",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = fields


class SyncConflictResolveSerializer(serializers.Serializer):
    choose = serializers.ChoiceField(choices=["sheet", "local"])
