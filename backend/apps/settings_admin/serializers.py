from rest_framework import serializers

from apps.bids.models import Bid, BidEngagement, Client, Person, Team
from apps.sync.normalizers import norm_text

from .capabilities import CAPABILITIES, ROLE_DEFAULT_CAPABILITIES
from .models import (
    ChoiceList,
    ChoiceValue,
    DeadlineReminderRule,
    EmailServiceSettings,
    NotificationPolicy,
    SheetAppendSettings,
    SyncScheduleSettings,
    UserCapability,
    WelcomeEmailSettings,
)


class SettingsClientSerializer(serializers.ModelSerializer):
    usage_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ["id", "name", "canonical_name", "usage_count"]
        read_only_fields = ["id", "canonical_name", "usage_count"]

    def get_usage_count(self, obj):
        return obj.bids.count()

    def validate_name(self, value):
        # canonical_name is read-only here and derived below, same rule the
        # sync's resolve_client() uses (§6/§8) — a manually created client
        # must match sheet rows the identical way a synced one would.
        canonical = norm_text(value)
        if not canonical:
            raise serializers.ValidationError("Enter a client name.")
        existing = Client.objects.filter(canonical_name__iexact=canonical)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("A client with this name already exists.")
        return value

    def create(self, validated_data):
        validated_data["canonical_name"] = norm_text(validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            validated_data["canonical_name"] = norm_text(validated_data["name"])
        return super().update(instance, validated_data)


class SettingsPersonSerializer(serializers.ModelSerializer):
    """§Phase 20 item 2's enhanced management screen — name, email,
    internal/external, organization, phone, active, linked user account and
    usage_count, with inline create/edit in mind (no separate write serializer;
    every field but the read-only ones is editable via PATCH)."""

    usage_count = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source="user.email", read_only=True, default=None)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True, default=None)

    class Meta:
        model = Person
        fields = [
            "id",
            "canonical_name",
            "aliases",
            "email",
            "person_type",
            "organization",
            "phone",
            "is_active",
            "user",
            "user_email",
            "user_full_name",
            "usage_count",
        ]
        read_only_fields = ["id", "aliases", "user_email", "user_full_name", "usage_count"]

    def get_usage_count(self, obj):
        return (
            obj.bids_as_cam.count() + obj.bids_as_sales_resource.count() + obj.bids_as_bid_manager.count()
            + obj.engaged_bids.count()
        )

    def validate_canonical_name(self, value):
        # Same whitespace normalization and case-insensitive identity as
        # resolve_person() (§8) — otherwise a manually added "John Doe" and a
        # sheet-synced "john doe" would silently become two different people.
        normalized = norm_text(value)
        if not normalized:
            raise serializers.ValidationError("Enter a name.")
        existing = Person.objects.filter(canonical_name__iexact=normalized)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("A person with this name already exists.")
        return normalized

    def validate_email(self, value):
        if not value:
            return value
        existing = Person.objects.filter(email__iexact=value)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("A person with this email already exists.")
        return value


class EngagementBidSummarySerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = Bid
        fields = ["id", "reference", "client_name", "submission_date", "stage", "result"]


class PersonEngagementSerializer(serializers.ModelSerializer):
    """One row of a person's engagement history (§Phase 20 item 4) — the
    bid it's on, days/dates/convenience_bill, and welcome-email status so the
    same view can drive the send/resend button (§Phase 20 item 5)."""

    bid = EngagementBidSummarySerializer(read_only=True)

    class Meta:
        model = BidEngagement
        fields = [
            "id",
            "bid",
            "engaged_from",
            "engaged_to",
            "days",
            "convenience_bill",
            "note",
            "welcome_email_sent_at",
        ]


class PersonMergeSerializer(serializers.Serializer):
    duplicate_id = serializers.IntegerField()

    def validate_duplicate_id(self, value):
        if not Person.objects.filter(pk=value).exists():
            raise serializers.ValidationError("No such person.")
        return value


class WelcomeEmailSettingsSerializer(serializers.ModelSerializer):
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True, default=None)

    class Meta:
        model = WelcomeEmailSettings
        fields = ["enabled", "updated_by_email", "updated_at"]
        read_only_fields = ["updated_by_email", "updated_at"]


class SheetAppendSettingsSerializer(serializers.ModelSerializer):
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True, default=None)

    class Meta:
        model = SheetAppendSettings
        fields = ["enabled", "updated_by_email", "updated_at"]
        read_only_fields = ["updated_by_email", "updated_at"]


class SyncScheduleSettingsSerializer(serializers.ModelSerializer):
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True, default=None)
    interval_hours = serializers.IntegerField(min_value=1, max_value=168)

    class Meta:
        model = SyncScheduleSettings
        fields = ["interval_hours", "updated_by_email", "updated_at"]
        read_only_fields = ["updated_by_email", "updated_at"]


class EmailServiceSettingsSerializer(serializers.ModelSerializer):
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True, default=None)

    class Meta:
        model = EmailServiceSettings
        fields = ["enabled", "updated_by_email", "updated_at"]
        read_only_fields = ["updated_by_email", "updated_at"]


class SettingsTeamSerializer(serializers.ModelSerializer):
    usage_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "name", "is_active", "usage_count"]
        read_only_fields = ["id", "usage_count"]

    def get_usage_count(self, obj):
        return obj.bids.count()

    def validate_name(self, value):
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError("Enter a team name.")
        existing = Team.objects.filter(name__iexact=trimmed)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("A team with this name already exists.")
        return trimmed


class ChoiceListSerializer(serializers.ModelSerializer):
    values_count = serializers.IntegerField(source="values.count", read_only=True)

    class Meta:
        model = ChoiceList
        fields = ["id", "key", "label", "description", "is_locked", "values_count"]
        read_only_fields = ["id", "key", "is_locked", "values_count"]


class ChoiceValueSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True, default=None)
    usage_count = serializers.SerializerMethodField()

    class Meta:
        model = ChoiceValue
        fields = [
            "id",
            "list",
            "value",
            "label",
            "sort_order",
            "is_active",
            "is_default",
            "created_by_sync",
            "created_by",
            "created_by_email",
            "created_at",
            "usage_count",
        ]
        read_only_fields = ["id", "list", "created_by_sync", "created_by", "created_by_email", "created_at"]

    def get_usage_count(self, obj):
        from apps.bids.models import Bid

        from .services import CHOICE_LIST_FIELD_MAP

        field_name = CHOICE_LIST_FIELD_MAP.get(obj.list.key)
        if field_name is None:
            flag_map = {"goods": "is_goods", "works": "is_works", "service": "is_service"}
            bool_field = flag_map.get(obj.value)
            return Bid.all_objects.filter(**{bool_field: True}).count() if bool_field else 0
        return Bid.all_objects.filter(**{field_name: obj.value}).count()


class ChoiceValueRenameSerializer(serializers.Serializer):
    new_value = serializers.CharField(max_length=150)
    new_label = serializers.CharField(max_length=150, required=False)

    def validate(self, attrs):
        attrs.setdefault("new_label", attrs["new_value"])
        return attrs


class ChoiceValueReorderSerializer(serializers.Serializer):
    order = serializers.ListField(child=serializers.IntegerField())


class CapabilityReferenceSerializer(serializers.Serializer):
    capabilities = serializers.SerializerMethodField()
    role_defaults = serializers.SerializerMethodField()

    def get_capabilities(self, obj):
        return CAPABILITIES

    def get_role_defaults(self, obj):
        return {role: sorted(caps) for role, caps in ROLE_DEFAULT_CAPABILITIES.items()}


class UserCapabilityGrantSerializer(serializers.Serializer):
    capability = serializers.ChoiceField(choices=CAPABILITIES)
    granted = serializers.BooleanField()


class UserCapabilityOverrideSerializer(serializers.ModelSerializer):
    granted_by_email = serializers.EmailField(source="granted_by.email", read_only=True, default=None)

    class Meta:
        model = UserCapability
        fields = ["capability", "granted", "granted_by_email", "granted_at"]
        read_only_fields = fields


class NotificationPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPolicy
        fields = ["id", "event_key", "label", "default_in_app", "default_email", "applies_to_roles", "is_active"]
        read_only_fields = ["id", "event_key"]


class DeadlineReminderRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeadlineReminderRule
        fields = ["id", "days_before", "is_active", "applies_to_roles", "users"]
        read_only_fields = ["id", "days_before"]
