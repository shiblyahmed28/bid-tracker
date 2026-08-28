from decimal import Decimal, InvalidOperation

from django.db import models as dj_models
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin

from apps.accounts.permissions import IsAdmin, IsEditorOrAbove
from apps.accounts.utils import get_client_ip, get_user_agent
from apps.audit.models import AuditEntry
from apps.bids.pagination import StandardPagination

from .models import QuarantineRow, SyncConflict, SyncRun
from .resolvers import resolve_client, resolve_person
from .serializers import (
    QuarantineRowSerializer,
    SyncConflictResolveSerializer,
    SyncConflictSerializer,
    SyncRunSerializer,
)
from .sync import run_sync


class SyncRunTriggerView(APIView):
    """POST /sync/run/ — admin only (§9, §11)."""

    permission_classes = [IsAdmin]

    def post(self, request):
        sync_run, _counts = run_sync(trigger=SyncRun.Trigger.MANUAL, actor=request.user)
        AuditEntry.objects.create(
            actor=request.user,
            actor_label=request.user.email,
            action=AuditEntry.Action.MANUAL_SYNC_TRIGGER,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return Response(SyncRunSerializer(sync_run).data, status=status.HTTP_201_CREATED)


class SyncRunListView(generics.ListAPIView):
    """GET /sync/runs/ — admin only (§11: "Sync history & quarantine")."""

    permission_classes = [IsAdmin]
    serializer_class = SyncRunSerializer
    pagination_class = StandardPagination
    queryset = SyncRun.objects.select_related("actor").all()


class QuarantineRowListView(generics.ListAPIView):
    """GET /sync/quarantine/ — admin only."""

    permission_classes = [IsAdmin]
    serializer_class = QuarantineRowSerializer
    pagination_class = StandardPagination
    queryset = QuarantineRow.objects.select_related("sync_run").all()


def _coerce_conflict_value(bid, field_name, raw, cache):
    """Reverses a SyncConflict's stringified sheet_value back into the typed
    value apply_change() needs. Every conflictable field is either a plain
    scalar or a Client/Person FK (§9's sheet_values in sync.py), so this is
    a closed set of cases, not general-purpose deserialization."""
    field = bid._meta.get_field(field_name)

    if raw == "":
        return None

    if field.is_relation:
        resolver = resolve_client if field_name == "client" else resolve_person
        return resolver(cache, raw)
    if isinstance(field, dj_models.DecimalField):
        try:
            return Decimal(raw)
        except InvalidOperation:
            return None
    if isinstance(field, dj_models.DateField):
        return parse_date(raw)
    if isinstance(field, dj_models.TimeField):
        return parse_time(raw)
    if isinstance(field, dj_models.BooleanField):
        return raw == "True"
    return raw


class SyncConflictViewSet(ListModelMixin, GenericViewSet):
    """GET /sync/conflicts/ · POST /sync/conflicts/{id}/resolve/ — editor+
    (§11: "resolve conflicts" is grouped with create/edit bid, not with the
    admin-only sync history/quarantine)."""

    permission_classes = [IsEditorOrAbove]
    serializer_class = SyncConflictSerializer
    pagination_class = StandardPagination
    queryset = SyncConflict.objects.select_related("bid", "bid__client", "local_editor", "resolved_by").all()

    def get_queryset(self):
        qs = super().get_queryset()
        resolved = self.request.query_params.get("resolved")
        if resolved is not None:
            qs = qs.filter(resolved=resolved.lower() == "true")
        bid_id = self.request.query_params.get("bid")
        if bid_id:
            qs = qs.filter(bid_id=bid_id)
        return qs.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        conflict = self.get_object()
        serializer = SyncConflictResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        choice = serializer.validated_data["choose"]

        bid = conflict.bid
        if choice == "sheet":
            value = _coerce_conflict_value(bid, conflict.field, conflict.sheet_value, {})
            overridden = list(bid.locally_overridden)
            if conflict.field in overridden:
                overridden.remove(conflict.field)
                bid.locally_overridden = overridden
                bid.save(update_fields=["locally_overridden"])
            bid.apply_change(conflict.field, value, actor=None)
        # choice == "local": the bid already holds the local value — nothing
        # to change, and locally_overridden stays set so it keeps protecting
        # this field on future syncs.

        conflict.resolved = True
        conflict.resolution = choice
        conflict.resolved_by = request.user
        conflict.resolved_at = timezone.now()
        conflict.save(update_fields=["resolved", "resolution", "resolved_by", "resolved_at"])

        AuditEntry.objects.create(
            actor=request.user,
            actor_label=request.user.email,
            action=AuditEntry.Action.CONFLICT_RESOLUTION,
            bid=bid,
            field=conflict.field,
            old_value=conflict.local_value,
            new_value=conflict.sheet_value if choice == "sheet" else conflict.local_value,
        )
        return Response(SyncConflictSerializer(conflict).data)
