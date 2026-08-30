from decimal import Decimal

from rest_framework import serializers

from .models import Bid, BidCostLine, BidEngagement, BidNote, Client, Person, Team


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


class BidEngagementDetailSerializer(serializers.ModelSerializer):
    """One row of the detail page's engagement table (§Phase 22 item 2)."""

    person = PersonSerializer(read_only=True)

    class Meta:
        model = BidEngagement
        fields = ["id", "person", "engaged_from", "engaged_to", "days", "convenience_bill", "note"]
        read_only_fields = fields


class BidCostLineDetailSerializer(serializers.ModelSerializer):
    """One row of the detail page's cost-line table (§Phase 22 item 2).
    `line_number` is only populated when the queryset ran
    BidCostLine.objects.with_line_number() — see get_cost_lines below."""

    line_number = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = BidCostLine
        fields = ["id", "line_number", "description", "date", "reference", "amount", "currency", "category"]
        read_only_fields = fields


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
    # §Phase 22 item 3 — the *summary* figure only (per currency), for the
    # dashboard KPI and this register column. None unless the queryset ran
    # .with_management_cost() — same defensive convention as get_serial()
    # above, so a call site that forgets the annotation degrades to "—"
    # instead of an AttributeError.
    management_cost_bdt = serializers.SerializerMethodField()
    management_cost_usd = serializers.SerializerMethodField()

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
            "management_cost_bdt",
            "management_cost_usd",
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

    def get_management_cost_bdt(self, obj):
        return getattr(obj, "management_cost_bdt", None)

    def get_management_cost_usd(self, obj):
        return getattr(obj, "management_cost_usd", None)


class BidDetailSerializer(BidListSerializer):
    """Everything the list gives you, plus conflict state, audit-relevant
    bookkeeping fields (§13's "Details" page), and the full cost breakdown
    (§Phase 22 item 2) — the register/dashboard only ever get the summary
    figure above, this is the only place the underlying rows are exposed."""

    conflicts = serializers.SerializerMethodField()
    has_unresolved_conflicts = serializers.SerializerMethodField()
    locally_overridden = serializers.ReadOnlyField()
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True, default=None)
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True, default=None)

    engagements = BidEngagementDetailSerializer(many=True, read_only=True)
    cost_lines = serializers.SerializerMethodField()
    total_engagement_days = serializers.ReadOnlyField()
    total_convenience_bill = serializers.ReadOnlyField()
    total_cost_lines = serializers.ReadOnlyField()
    management_cost = serializers.ReadOnlyField()

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
            "engagements",
            "cost_lines",
            "total_engagement_days",
            "total_convenience_bill",
            "total_cost_lines",
            "management_cost",
        ]

    def get_conflicts(self, obj):
        unresolved = obj.sync_conflicts.filter(resolved=False).order_by("-created_at")
        return ConflictSummarySerializer(unresolved, many=True).data

    def get_has_unresolved_conflicts(self, obj):
        return obj.sync_conflicts.filter(resolved=False).exists()

    def get_cost_lines(self, obj):
        return BidCostLineDetailSerializer(obj.cost_lines.with_line_number(), many=True).data


class BidEngagementWriteSerializer(serializers.Serializer):
    """One repeatable engagement row from the create/edit form (§Phase 22
    item 4) — a superset of the old plain engaged_resources PK list: adding
    someone with every optional field left at its default is exactly
    equivalent to the old "just check the box"."""

    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())
    engaged_from = serializers.DateField(required=False, allow_null=True, default=None)
    engaged_to = serializers.DateField(required=False, allow_null=True, default=None)
    days = serializers.IntegerField(required=False, default=0, min_value=0)
    convenience_bill = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=Decimal("0"), min_value=Decimal("0")
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")


class BidCostLineWriteSerializer(serializers.Serializer):
    """One repeatable cost-line row from the create/edit form (§Phase 22 item 4)."""

    description = serializers.CharField()
    date = serializers.DateField(required=False, allow_null=True, default=None)
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    currency = serializers.ChoiceField(choices=Bid.Currency.choices, default=Bid.Currency.BDT)
    category = serializers.CharField(required=False, allow_blank=True, default="")


class BidWriteSerializer(serializers.ModelSerializer):
    """Create/update, routed through Bid.apply_change by the view (§17). Only
    client, description and submission_date are required (§13's "title +
    submission date"); everything else is optional. client/cam/sales_resource/
    bid_manager are free-text names resolved like the sync pipeline does
    (apps.sync.resolvers) — team is app-native (§7) and picked from the
    existing, curated list instead. `engagements`/`cost_lines` (§Phase 22
    item 4) replace the old flat `engaged_resources` PK list — the view
    (BidViewSet._sync_engagements/_sync_cost_lines) does the actual
    BidEngagement/BidCostLine row sync, not this serializer.
    """

    client_name = serializers.CharField()
    cam_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sales_resource_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    bid_manager_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    engagements = BidEngagementWriteSerializer(many=True, required=False)
    cost_lines = BidCostLineWriteSerializer(many=True, required=False)

    class Meta:
        model = Bid
        fields = [
            "client_name",
            "description",
            "cam_name",
            "sales_resource_name",
            "bid_manager_name",
            "team",
            "engagements",
            "cost_lines",
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
