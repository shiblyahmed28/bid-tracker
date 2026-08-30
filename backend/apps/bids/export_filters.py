"""Shared between the sync and async (Celery) export paths: apply the same
filters /bids/ uses, and describe them in one human-readable caption line
for the PDF (§13: "a caption line stating the filters applied")."""

from django.db.models import Q
from django.utils.dateparse import parse_date

from .filters import BidFilter
from .models import Bid, Team

SEARCH_FIELDS = ["client__name", "description", "tender_id", "bid_manager__canonical_name"]

# param -> human label, in the order they should appear in the caption.
FILTER_PARAM_LABELS = [
    ("client", "Client"),
    ("team", "Team"),
    ("stage", "Stage"),
    ("procurement_type", "Procurement type"),
    ("initiation_mode", "Initiation mode"),
    ("delivery_type", "Delivery type"),
    ("cam", "CAM"),
    ("sales_resource", "Sales resource"),
    ("bid_manager", "Bid manager"),
    ("security_mode", "Security mode"),
    ("bg_bank", "Issuing bank"),
    ("submission_status", "Submission status"),
    ("result", "Result"),
    ("source", "Source"),
    ("description", "Description"),
    ("tender_id", "Tender ID"),
    ("engaged_resources", "Engaged resources"),
    ("security_amount_raw", "Security amount"),
    ("credit_facility_raw", "Credit facility"),
    ("bg_reference", "BG / reference no."),
    ("remarks", "Remarks"),
]


def apply_search(queryset, search_term):
    if not search_term:
        return queryset
    query = Q()
    for field in SEARCH_FIELDS:
        query |= Q(**{f"{field}__icontains": search_term})
    return queryset.filter(query)


def filtered_export_queryset(queryset, query_params):
    queryset = BidFilter(query_params, queryset=queryset).qs
    queryset = apply_search(queryset, query_params.get("search"))
    # §Phase 22 item 3's management_cost column reads the annotated
    # management_cost_bdt/usd, not Bid.management_cost's per-instance
    # aggregate — a full-register CSV/PDF export iterates every filtered
    # row, so the per-instance property would be an N+1 query multiplier.
    queryset = queryset.with_management_cost()
    # Newest first (§18 Phase 18 item 1) — matches the register/API default,
    # so PDF and CSV exports read top-to-bottom the same as the on-screen table.
    return queryset.order_by("-arrival_seq")


def _format_date_param(value):
    parsed = parse_date(value) if value else None
    return parsed.strftime("%d %b %Y") if parsed else value


def describe_filters(query_params):
    parts = []

    search = query_params.get("search")
    if search:
        parts.append(f'Search: "{search}"')

    date_from = query_params.get("submission_after")
    date_to = query_params.get("submission_before")
    if date_from or date_to:
        parts.append(f"Dates: {_format_date_param(date_from) or '…'} → {_format_date_param(date_to) or '…'}")
    else:
        parts.append("Dates: all")

    for param, label in FILTER_PARAM_LABELS:
        value = query_params.get(param)
        if not value:
            continue
        if param == "team":
            team = Team.objects.filter(id=value).first()
            value = team.name if team else value
        parts.append(f"{label}: {value}")

    return " · ".join(parts)
