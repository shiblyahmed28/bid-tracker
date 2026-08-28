import django_filters

from .models import Bid


class BidFilter(django_filters.FilterSet):
    """One filter per column (§13): enum columns match exactly (dropdown of
    distinct values), text/list/money columns are contains-matches. All
    combine with AND; `search` (view-level SearchFilter) is the one OR box.
    """

    client = django_filters.CharFilter(field_name="client__name", lookup_expr="icontains")
    cam = django_filters.CharFilter(field_name="cam__canonical_name", lookup_expr="icontains")
    sales_resource = django_filters.CharFilter(field_name="sales_resource__canonical_name", lookup_expr="icontains")
    bid_manager = django_filters.CharFilter(field_name="bid_manager__canonical_name", lookup_expr="icontains")
    description = django_filters.CharFilter(lookup_expr="icontains")
    tender_id = django_filters.CharFilter(lookup_expr="icontains")
    remarks = django_filters.CharFilter(lookup_expr="icontains")

    stage = django_filters.CharFilter(lookup_expr="iexact")
    initiation_mode = django_filters.CharFilter(lookup_expr="iexact")
    procurement_type = django_filters.CharFilter(lookup_expr="iexact")
    submission_status = django_filters.CharFilter(lookup_expr="iexact")
    result = django_filters.CharFilter(lookup_expr="iexact")
    security_mode = django_filters.CharFilter(lookup_expr="iexact")
    source = django_filters.CharFilter(lookup_expr="iexact")

    is_goods = django_filters.BooleanFilter()
    is_works = django_filters.BooleanFilter()
    is_service = django_filters.BooleanFilter()
    missing_from_sheet = django_filters.BooleanFilter()

    team = django_filters.NumberFilter(field_name="team_id")
    engaged = django_filters.NumberFilter(field_name="engaged_resources", label="Engaged resource (person id)")

    security_amount_raw = django_filters.CharFilter(lookup_expr="icontains")
    credit_facility_raw = django_filters.CharFilter(lookup_expr="icontains")

    bg_bank = django_filters.CharFilter(lookup_expr="iexact")
    bg_reference = django_filters.CharFilter(lookup_expr="icontains")

    # §13's "list" column type (Engaged resources): a contains-match against
    # the joined names, distinct from `engaged` (exact match by person id).
    engaged_resources = django_filters.CharFilter(method="filter_engaged_resources")

    # Delivery type isn't a real column — it's is_goods/is_works/is_service
    # collapsed into one enum-style value ("Goods, Service") for the register
    # (§13), so filtering it means matching that exact combination.
    delivery_type = django_filters.CharFilter(method="filter_delivery_type")

    submission_after = django_filters.DateFilter(field_name="submission_date", lookup_expr="gte")
    submission_before = django_filters.DateFilter(field_name="submission_date", lookup_expr="lte")

    def filter_engaged_resources(self, queryset, name, value):
        return queryset.filter(engaged_resources__canonical_name__icontains=value).distinct()

    def filter_delivery_type(self, queryset, name, value):
        wanted = {part.strip().lower() for part in value.split(",") if part.strip()}
        return queryset.filter(
            is_goods=("goods" in wanted), is_works=("works" in wanted), is_service=("service" in wanted)
        )

    class Meta:
        model = Bid
        fields = [
            "client",
            "cam",
            "sales_resource",
            "bid_manager",
            "description",
            "tender_id",
            "remarks",
            "stage",
            "initiation_mode",
            "procurement_type",
            "submission_status",
            "result",
            "security_mode",
            "source",
            "is_goods",
            "is_works",
            "is_service",
            "missing_from_sheet",
            "team",
            "engaged",
            "engaged_resources",
            "delivery_type",
            "security_amount_raw",
            "credit_facility_raw",
            "bg_bank",
            "bg_reference",
            "submission_after",
            "submission_before",
        ]
