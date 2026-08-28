from datetime import timedelta

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin, IsAuthenticatedViewer, IsEditorOrAbove
from apps.audit.models import AuditEntry
from apps.audit.serializers import AuditEntrySerializer
from apps.sync.resolvers import resolve_client, resolve_person

from .filters import BidFilter
from .models import Bid
from .pagination import StandardPagination
from .serializers import BidDetailSerializer, BidListSerializer, BidWriteSerializer

SELECT_RELATED = ("client", "cam", "sales_resource", "bid_manager", "team", "created_by", "updated_by")
PREFETCH_RELATED = ("engaged_resources",)

# Keys on BidWriteSerializer.validated_data that need Person/Client resolution
# before they map onto real Bid fields (mirrors apps.sync.sync.RESOLVED_KEYS).
NAME_FIELD_TO_FK = {
    "client_name": ("client", resolve_client),
    "cam_name": ("cam", resolve_person),
    "sales_resource_name": ("sales_resource", resolve_person),
    "bid_manager_name": ("bid_manager", resolve_person),
}


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
    ordering = ["arrival_seq"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsEditorOrAbove()]
        if self.action == "destroy":
            return [IsAdmin()]
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
            qs = self._apply_default_date_window(qs)
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
        instance = Bid.objects.select_related(*SELECT_RELATED).prefetch_related(*PREFETCH_RELATED).with_serial().get(pk=bid.pk)
        serializer = BidDetailSerializer(instance, context=self.get_serializer_context())
        return Response(serializer.data, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bid = self._create_bid(serializer.validated_data)
        return self._detail_response(bid, status.HTTP_201_CREATED)

    def _create_bid(self, validated_data):
        data = dict(validated_data)
        engaged_resources = data.pop("engaged_resources", [])

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
        if engaged_resources:
            bid.engaged_resources.set(engaged_resources)

        AuditEntry.objects.create(
            actor=self.request.user,
            actor_label=self.request.user.email,
            action=AuditEntry.Action.BID_CREATE,
            bid=bid,
        )
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

        engaged_resources = data.pop("engaged_resources", None)

        for field_name, new_value in data.items():
            current_value = getattr(instance, field_name)
            if current_value != new_value:
                instance.apply_change(field_name, new_value, actor=self.request.user)

        if engaged_resources is not None:
            current_ids = set(instance.engaged_resources.values_list("pk", flat=True))
            new_ids = {person.pk for person in engaged_resources}
            if current_ids != new_ids:
                instance.apply_change("engaged_resources", engaged_resources, actor=self.request.user)

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
