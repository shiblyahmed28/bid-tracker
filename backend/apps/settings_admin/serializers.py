from rest_framework import serializers

from apps.bids.models import Client, Person, Team
from apps.sync.normalizers import norm_text

from .capabilities import CAPABILITIES, ROLE_DEFAULT_CAPABILITIES
from .models import (
    ChoiceList,
    ChoiceValue,
    DeadlineReminderRule,
    NotificationPolicy,
    UserCapability,
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
    usage_count = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "canonical_name", "aliases", "usage_count"]
        read_only_fields = ["id", "usage_count"]

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
