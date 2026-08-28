from rest_framework import serializers

from .models import Bid, BidNote, Client, Person, Team


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "is_active"]


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ["id", "canonical_name", "aliases"]


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "name", "canonical_name"]


class BidNoteSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True, default=None)

    class Meta:
        model = BidNote
        fields = ["id", "body", "author", "author_email", "created_at"]
        read_only_fields = ["id", "author", "author_email", "created_at"]


class ConflictSummarySerializer(serializers.Serializer):
    """A bid's own unresolved SyncConflicts, for the detail page's conflict state."""

    id = serializers.IntegerField()
    field = serializers.CharField()
    sheet_value = serializers.CharField()
    local_value = serializers.CharField()
    local_editor = serializers.CharField(source="local_editor.email", default=None)
    local_edited_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()


class BidListSerializer(serializers.ModelSerializer):
    """The register (§13) — a subset of columns; the column picker lives in
    the frontend, this just needs to carry every column it might show."""

    serial = serializers.SerializerMethodField()
    client = ClientSerializer(read_only=True)
    cam = PersonSerializer(read_only=True)
    sales_resource = PersonSerializer(read_only=True)
    bid_manager = PersonSerializer(read_only=True)
    team = TeamSerializer(read_only=True)
    engaged_resources = PersonSerializer(many=True, read_only=True)
    engagement_days = serializers.ReadOnlyField()

    class Meta:
        model = Bid
        fields = [
            "id",
            "serial",
            "reference",
            "source",
            "client",
            "description",
            "cam",
            "sales_resource",
            "bid_manager",
            "team",
            "engaged_resources",
            "engagement_from",
            "engagement_to",
            "engagement_days",
            "stage",
            "initiation_mode",
            "procurement_type",
            "is_goods",
            "is_works",
            "is_service",
            "tender_id",
            "initiation_date",
            "published_date",
            "prebid_date",
            "prebid_time",
            "submission_date",
            "submission_time",
            "submission_status",
            "result",
            "security_mode",
            "security_amount_raw",
            "security_amount",
            "security_currency",
            "credit_facility_raw",
            "credit_facility",
            "credit_facility_currency",
            "bg_issue_date",
            "bg_reference",
            "bg_bank",
            "bg_expiry_date",
            "remarks",
            "missing_from_sheet",
            "is_deleted",
        ]

    def get_serial(self, obj):
        # None unless the queryset ran .with_serial() — defensive rather than
        # assuming every call site remembered to annotate it.
        return getattr(obj, "serial", None)


class BidDetailSerializer(BidListSerializer):
    """Everything the list gives you, plus conflict state and audit-relevant
    bookkeeping fields (§13's "Details" page)."""

    conflicts = serializers.SerializerMethodField()
    has_unresolved_conflicts = serializers.SerializerMethodField()
    locally_overridden = serializers.ReadOnlyField()
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True, default=None)
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True, default=None)

    class Meta(BidListSerializer.Meta):
        fields = BidListSerializer.Meta.fields + [
            "uid",
            "sheet_row",
            "locally_overridden",
            "conflicts",
            "has_unresolved_conflicts",
            "created_by",
            "created_by_email",
            "updated_by",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]

    def get_conflicts(self, obj):
        unresolved = obj.sync_conflicts.filter(resolved=False).order_by("-created_at")
        return ConflictSummarySerializer(unresolved, many=True).data

    def get_has_unresolved_conflicts(self, obj):
        return obj.sync_conflicts.filter(resolved=False).exists()


class BidWriteSerializer(serializers.ModelSerializer):
    """Create/update, routed through Bid.apply_change by the view (§17). Only
    client, description and submission_date are required (§13's "title +
    submission date"); everything else is optional. client/cam/sales_resource/
    bid_manager are free-text names resolved like the sync pipeline does
    (apps.sync.resolvers) — team and engaged_resources are app-native (§7)
    and picked from the existing, curated lists instead.
    """

    client_name = serializers.CharField()
    cam_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sales_resource_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    bid_manager_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    engaged_resources = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Person.objects.all(), required=False
    )

    class Meta:
        model = Bid
        fields = [
            "client_name",
            "description",
            "cam_name",
            "sales_resource_name",
            "bid_manager_name",
            "team",
            "engaged_resources",
            "engagement_from",
            "engagement_to",
            "stage",
            "initiation_mode",
            "procurement_type",
            "is_goods",
            "is_works",
            "is_service",
            "tender_id",
            "initiation_date",
            "published_date",
            "prebid_date",
            "prebid_time",
            "submission_date",
            "submission_time",
            "submission_status",
            "result",
            "security_mode",
            "security_amount_raw",
            "security_amount",
            "security_currency",
            "credit_facility_raw",
            "credit_facility",
            "credit_facility_currency",
            "bg_issue_date",
            "bg_reference",
            "bg_bank",
            "bg_expiry_date",
            "remarks",
        ]
        extra_kwargs = {
            "description": {"required": True, "allow_blank": False},
            "submission_date": {"required": True},
        }

    def validate_client_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("This field is required.")
        return value.strip()
