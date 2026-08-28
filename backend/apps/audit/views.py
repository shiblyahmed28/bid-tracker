import csv

from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.views import APIView

from apps.bids.pagination import StandardPagination
from apps.settings_admin.capabilities import HasCapability

from .filters import AuditEntryFilter
from .models import AuditEntry
from .serializers import AuditEntrySerializer

QUERYSET = AuditEntry.objects.select_related("actor", "bid").all()

CSV_COLUMNS = [
    "id",
    "actor_email",
    "actor_label",
    "action",
    "bid_reference",
    "field",
    "old_value",
    "new_value",
    "ip",
    "user_agent",
    "created_at",
]


class AuditEntryListView(generics.ListAPIView):
    """GET /audit/ — requires view_audit_log (§11, §15)."""

    permission_classes = [HasCapability("view_audit_log")]
    serializer_class = AuditEntrySerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = AuditEntryFilter
    queryset = QUERYSET


class AuditEntryExportView(APIView):
    """GET /audit/export/ — requires view_audit_log, same filters as the list, unpaginated CSV."""

    permission_classes = [HasCapability("view_audit_log")]

    def get(self, request):
        queryset = AuditEntryFilter(request.query_params, queryset=QUERYSET).qs

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit-log.csv"'
        writer = csv.writer(response)
        writer.writerow(CSV_COLUMNS)
        for entry in queryset.iterator():
            writer.writerow(
                [
                    entry.id,
                    entry.actor.email if entry.actor else "",
                    entry.actor_label,
                    entry.action,
                    entry.bid.reference if entry.bid else "",
                    entry.field,
                    entry.old_value or "",
                    entry.new_value or "",
                    entry.ip or "",
                    entry.user_agent,
                    entry.created_at.isoformat(),
                ]
            )
        return response
