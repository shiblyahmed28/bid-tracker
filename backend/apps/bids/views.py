from datetime import timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedViewer
from apps.audit.models import AuditEntry
from apps.audit.serializers import AuditEntrySerializer
from apps.settings_admin.capabilities import HasCapability
from apps.sync.resolvers import resolve_client, resolve_person

from .filters import BidFilter
from .models import Bid, BidCostLine, BidEngagement, Person, Team
from .pagination import StandardPagination
from .pdf import render_bid_detail_pdf
from .serializers import BidDetailSerializer, BidListSerializer, BidWriteSerializer, PersonSerializer


class PersonListView(generics.ListAPIView):
    """GET /people/ — the full roster for the engaged_resources multi-select
    (§7, §11 create/edit form) and similar person pickers. Unpaginated —
    there are only a few dozen real rows, comfortably one response."""

    permission_classes = [IsAuthenticatedViewer]
    serializer_class = PersonSerializer
    pagination_class = None
    queryset = Person.objects.order_by("canonical_name")

SELECT_RELATED = ("client", "cam", "sales_resource", "bid_manager", "team", "created_by", "updated_by")
PREFETCH_RELATED = ("engaged_resources",)
# Detail-only — the list/register never renders the per-row breakdown
# (§Phase 22 item 3), so these prefetches would be wasted there.
DETAIL_PREFETCH_RELATED = PREFETCH_RELATED + ("engagements__person", "cost_lines")

# Register column key -> underlying field for a plain distinct-values lookup
# (§13: "enum columns get a dropdown of distinct values"). `team` and
# `delivery_type` are handled specially below — team needs an id, not a
# name, and delivery_type isn't a real column at all.
DISTINCT_TEXT_FIELDS = {
    "client": "client__name",
    "stage": "stage",
    "procurement_type": "procurement_type",
    "initiation_mode": "initiation_mode",
    "cam": "cam__canonical_name",
    "sales_resource": "sales_resource__canonical_name",
    "bid_manager": "bid_manager__canonical_name",
    "security_mode": "security_mode",
    "bg_bank": "bg_bank",
    "submission_status": "submission_status",
    "result": "result",
    "source": "source",
}


class BidDistinctValuesView(APIView):
    """GET /bids/distinct/?field=stage — unscoped by date range, matching
    the register's filter dropdowns (§13): you can filter to "Won" even if
    there are currently zero Won bids in the selected range."""

    permission_classes = [IsAuthenticatedViewer]

    def get(self, request):
        field = request.query_params.get("field", "")

        if field == "team":
            options = [{"value": str(team.id), "label": team.name} for team in Team.objects.order_by("name")]
            return Response({"field": field, "options": options})

        if field == "delivery_type":
            combos = Bid.objects.values_list("is_goods", "is_works", "is_service").distinct()
            labels = set()
            for is_goods, is_works, is_service in combos:
                parts = [name for present, name in [(is_goods, "Goods"), (is_works, "Works"), (is_service, "Service")] if present]
                if parts:
                    labels.add(", ".join(parts))
            options = [{"value": label, "label": label} for label in sorted(labels)]
            return Response({"field": field, "options": options})

        db_field = DISTINCT_TEXT_FIELDS.get(field)
        if db_field is None:
            return Response({"detail": f"Unknown field '{field}'."}, status=400)

        values = (
            Bid.objects.exclude(**{db_field: ""})
            .exclude(**{f"{db_field}__isnull": True})
            .order_by(db_field)
            .values_list(db_field, flat=True)
            .distinct()
        )
        return Response({"field": field, "options": [{"value": v, "label": v} for v in values]})

# Keys on BidWriteSerializer.validated_data that need Person/Client resolution
# before they map onto real Bid fields (mirrors apps.sync.sync.RESOLVED_KEYS).
NAME_FIELD_TO_FK = {
    "client_name": ("client", resolve_client),
    "cam_name": ("cam", resolve_person),
    "sales_resource_name": ("sales_resource", resolve_person),
    "bid_manager_name": ("bid_manager", resolve_person),
}


def _sync_engagements(bid, rows):
    """Full replace of this bid's BidEngagement rows, keyed by person
    (§Phase 22 item 4) — the repeatable row editor always resubmits the
    complete current set, so there's no per-row id to diff against.

    Returns (people, membership_changed, detail_changed) so the caller can
    still drive the pre-existing engaged_resources notification/audit path
    (Bid.apply_change) exactly when membership changes, same as before this
    phase — and fall back to a plain audit entry when only the per-person
    detail fields (days/dates/convenience_bill) changed."""
    existing = {e.person_id: e for e in bid.engagements.all()}
    seen_person_ids = set()
    detail_changed = False

    for row in rows:
        person = row["person"]
        seen_person_ids.add(person.id)
        defaults = {
            "engaged_from": row.get("engaged_from"),
            "engaged_to": row.get("engaged_to"),
            "days": row.get("days") or 0,
            "convenience_bill": row.get("convenience_bill") or Decimal("0"),
            "note": row.get("note") or "",
        }
        prior = existing.get(person.id)
        if prior is None or any(getattr(prior, key) != value for key, value in defaults.items()):
            detail_changed = True
        BidEngagement.objects.update_or_create(bid=bid, person=person, defaults=defaults)

    stale_person_ids = set(existing) - seen_person_ids
    if stale_person_ids:
        detail_changed = True
        bid.engagements.filter(person_id__in=stale_person_ids).delete()

    people = [row["person"] for row in rows]
    membership_changed = set(existing) != seen_person_ids
    return people, membership_changed, detail_changed


def _sync_cost_lines(bid, rows, actor):
    """Full replace of this bid's BidCostLine rows (§Phase 22 item 4) — cost
    lines have no natural identity to diff against across an edit (unlike
    engagements, which are keyed by person), so every save recreates them.
    Returns whether anything actually changed, for the audit entry."""
    old_signature = sorted(
        (line.description, line.date, line.reference, line.amount, line.currency, line.category)
        for line in bid.cost_lines.all()
    )
    bid.cost_lines.all().delete()
    for row in rows:
        BidCostLine.objects.create(
            bid=bid,
            created_by=actor,
            description=row["description"],
            date=row.get("date"),
            reference=row.get("reference") or "",
            amount=row["amount"],
            currency=row.get("currency") or Bid.Currency.BDT,
            category=row.get("category") or "",
        )
    new_signature = sorted(
        (
            row["description"],
            row.get("date"),
            row.get("reference") or "",
            row["amount"],
            row.get("currency") or Bid.Currency.BDT,
            row.get("category") or "",
        )
        for row in rows
    )
    return old_signature != new_signature


class BidViewSet(viewsets.ModelViewSet):
    """The register (§13) and its detail page. List/retrieve are viewer+;
    create/update are editor+, routed through Bid.apply_change so every
    manual edit gets an audit entry and — for sheet-owned fields — protection
    from the next sync silently overwriting it (§9). Soft delete is admin
    only (§11)."""

    queryset = Bid.objects.select_related(*SELECT_RELATED).prefetch_related(*PREFETCH_RELATED)
    lookup_field = "id"
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BidFilter
    search_fields = ["client__name", "description", "tender_id", "bid_manager__canonical_name"]
    ordering_fields = ["submission_date", "published_date", "created_at", "arrival_seq", "client__name"]
    # Newest first by default (§18 Phase 18 item 1) — an explicit ?ordering=
    # still overrides this in either direction.
    ordering = ["-arrival_seq"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [HasCapability("create_bid")()]
        if self.action in ("update", "partial_update"):
            return [HasCapability("edit_bid")()]
        if self.action == "destroy":
            return [HasCapability("delete_bid")()]
        if self.action == "export_pdf":
            return [HasCapability("export_pdf")()]
        return [IsAuthenticatedViewer()]

    def get_serializer_class(self):
        if self.action == "list":
            return BidListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BidWriteSerializer
        return BidDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ("list", "retrieve"):
            qs = qs.with_serial()
        if self.action == "list":
            qs = qs.with_management_cost()
            qs = self._apply_default_date_window(qs)
        if self.action in ("retrieve", "export_pdf"):
            qs = qs.prefetch_related(*("engagements__person", "cost_lines"))
        return qs

    def _apply_default_date_window(self, qs):
        """§12/§17: submission date, today-7 to today+7, when neither bound
        is given. An explicit submission_after/submission_before (applied
        afterward by BidFilter) fully overrides this, not layers onto it."""
        params = self.request.query_params
        if "submission_after" not in params and "submission_before" not in params:
            today = timezone.localdate()
            qs = qs.filter(
                submission_date__gte=today - timedelta(days=7),
                submission_date__lte=today + timedelta(days=7),
            )
        return qs

    def _detail_response(self, bid, status_code):
        instance = (
            Bid.objects.select_related(*SELECT_RELATED)
            .prefetch_related(*DETAIL_PREFETCH_RELATED)
            .with_serial()
            .get(pk=bid.pk)
        )
        serializer = BidDetailSerializer(instance, context=self.get_serializer_context())
        return Response(serializer.data, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bid = self._create_bid(serializer.validated_data)
        return self._detail_response(bid, status.HTTP_201_CREATED)

    def _create_bid(self, validated_data):
        data = dict(validated_data)
        engagements = data.pop("engagements", [])
        cost_lines = data.pop("cost_lines", [])

        cache = {}
        for name_field, (fk_field, resolver) in NAME_FIELD_TO_FK.items():
            if name_field in data:
                data[fk_field] = resolver(cache, data.pop(name_field))

        bid = Bid.objects.create(
            source=Bid.Source.APP,
            created_by=self.request.user,
            updated_by=self.request.user,
            **data,
        )
        if engagements:
            people, _membership_changed, _detail_changed = _sync_engagements(bid, engagements)
            bid.engaged_resources.set(people)
        if cost_lines:
            _sync_cost_lines(bid, cost_lines, self.request.user)

        AuditEntry.objects.create(
            actor=self.request.user,
            actor_label=self.request.user.email,
            action=AuditEntry.Action.BID_CREATE,
            bid=bid,
        )

        from apps.notifications.services import notify_new_bid

        notify_new_bid(bid)
        return bid

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self._apply_update(instance, serializer.validated_data)
        return self._detail_response(instance, status.HTTP_200_OK)

    def _apply_update(self, instance, validated_data):
        data = dict(validated_data)
        cache = {}
        for name_field, (fk_field, resolver) in NAME_FIELD_TO_FK.items():
            if name_field in data:
                data[fk_field] = resolver(cache, data.pop(name_field))

        engagements = data.pop("engagements", None)
        cost_lines = data.pop("cost_lines", None)

        from apps.settings_admin.services import notify_policy_transition

        for field_name, new_value in data.items():
            current_value = getattr(instance, field_name)
            if current_value != new_value:
                instance.apply_change(field_name, new_value, actor=self.request.user)
                notify_policy_transition(instance, field_name, str(current_value or ""), str(new_value or ""))

        if engagements is not None:
            people, membership_changed, detail_changed = _sync_engagements(instance, engagements)
            if membership_changed:
                # Membership is already correct on the DB from _sync_engagements
                # above — .set() here is a no-op, called purely so this still
                # goes through apply_change's existing audit-entry +
                # notify_field_change side effects, exactly as before Phase 22.
                instance.apply_change("engaged_resources", people, actor=self.request.user)
            elif detail_changed:
                AuditEntry.objects.create(
                    actor=self.request.user,
                    actor_label=self.request.user.email,
                    action=AuditEntry.Action.BID_UPDATE,
                    bid=instance,
                    field="engagements",
                    new_value=f"{len(people)} engaged resource(s) — details updated",
                )

        if cost_lines is not None:
            changed = _sync_cost_lines(instance, cost_lines, self.request.user)
            if changed:
                AuditEntry.objects.create(
                    actor=self.request.user,
                    actor_label=self.request.user.email,
                    action=AuditEntry.Action.BID_UPDATE,
                    bid=instance,
                    field="cost_lines",
                    new_value=f"{len(cost_lines)} cost line(s)",
                )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])
        AuditEntry.objects.create(
            actor=request.user,
            actor_label=request.user.email,
            action=AuditEntry.Action.BID_SOFT_DELETE,
            bid=instance,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def history(self, request, id=None):
        """GET /bids/{id}/history/ — newest first. Viewer+ (§15: "every bid
        detail page shows its own history"), unlike the admin-only global
        audit log."""
        bid = self.get_object()
        entries = AuditEntry.objects.filter(bid=bid).select_related("actor").order_by("-created_at")
        page = self.paginate_queryset(entries)
        serializer = AuditEntrySerializer(page if page is not None else entries, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="export/pdf")
    def export_pdf(self, request, id=None):
        """GET /bids/{id}/export/pdf/ — the per-bid PDF (§Phase 22 item 3):
        key details plus the full cost breakdown, unlike the register export
        (/bids/export/pdf/), which never carries more than the summary
        figure per bid."""
        bid = self.get_object()
        pdf_bytes = render_bid_detail_pdf(bid)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{bid.reference}.pdf"'
        return response
