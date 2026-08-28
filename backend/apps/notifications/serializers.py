from rest_framework import serializers

from .models import NOTIFICATION_FIELDS, DEFAULT_ON_FIELDS, Notification


class NotificationSerializer(serializers.ModelSerializer):
    bid_reference = serializers.CharField(source="bid.reference", default=None, read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "bid", "bid_reference", "read", "created_at"]
        read_only_fields = fields


class NotificationSettingsSerializer(serializers.Serializer):
    """GET/PATCH /notifications/settings/ — the four master switches plus the
    effective on/off state of every subscribable field (§16)."""

    notifications_muted = serializers.BooleanField(required=False)
    email_digest = serializers.BooleanField(required=False)
    email_deadline = serializers.BooleanField(required=False)
    email_newbid = serializers.BooleanField(required=False)
    fields = serializers.DictField(child=serializers.BooleanField(), required=False)

    def validate_fields(self, value):
        valid_keys = {key for key, _label in NOTIFICATION_FIELDS}
        unknown = set(value) - valid_keys
        if unknown:
            raise serializers.ValidationError(f"Unknown field(s): {', '.join(sorted(unknown))}")
        return value

    @staticmethod
    def represent(user):
        from .models import NotificationSubscription

        overrides = dict(
            NotificationSubscription.objects.filter(user=user).values_list("field_name", "enabled")
        )
        return {
            "notifications_muted": user.notifications_muted,
            "email_digest": user.email_digest,
            "email_deadline": user.email_deadline,
            "email_newbid": user.email_newbid,
            "fields": {
                key: overrides.get(key, key in DEFAULT_ON_FIELDS) for key, _label in NOTIFICATION_FIELDS
            },
            "field_labels": {key: label for key, label in NOTIFICATION_FIELDS},
        }
