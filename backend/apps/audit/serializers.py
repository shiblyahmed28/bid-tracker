from rest_framework import serializers

from .models import AuditEntry


class AuditEntrySerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)
    bid_reference = serializers.CharField(source="bid.reference", read_only=True, default=None)

    class Meta:
        model = AuditEntry
        fields = [
            "id",
            "actor",
            "actor_email",
            "actor_label",
            "action",
            "bid",
            "bid_reference",
            "field",
            "old_value",
            "new_value",
            "ip",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields
