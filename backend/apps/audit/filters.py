import django_filters

from .models import AuditEntry


class AuditEntryFilter(django_filters.FilterSet):
    """§15: filterable by user, action, bid and date range."""

    actor = django_filters.NumberFilter(field_name="actor_id")
    action = django_filters.CharFilter(lookup_expr="iexact")
    bid = django_filters.CharFilter(field_name="bid_id")
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = AuditEntry
        fields = ["actor", "action", "bid", "created_after", "created_before"]
