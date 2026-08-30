"""Column definitions for PDF/CSV export — mirrors frontend/src/register/
columns.tsx exactly (same 29 keys, labels, groups, defaults) so the two
never drift apart in what the register shows vs. what gets exported."""

from dataclasses import dataclass
from typing import Callable

from .models import Bid


def _dmy(date_obj):
    if not date_obj:
        return "—"
    return date_obj.strftime("%d %b %Y")


def _date_time_cell(date_obj, time_obj):
    if not date_obj:
        return "—"
    base = _dmy(date_obj)
    return f"{base}, {time_obj.strftime('%H:%M')}" if time_obj else base


def _name_or_dash(ref):
    return ref.canonical_name if ref else "—"


def _money_cell(raw):
    return raw or "—"


def _delivery_type(bid):
    parts = [name for present, name in [(bid.is_goods, "Goods"), (bid.is_works, "Works"), (bid.is_service, "Service")] if present]
    return ", ".join(parts) if parts else "—"


def _engaged_resources(bid):
    names = [p.canonical_name for p in bid.engaged_resources.all()]
    return ", ".join(names) if names else "—"


def _engagement_period(bid):
    if not bid.engagement_from:
        return "—"
    return f"{_dmy(bid.engagement_from)} → {_dmy(bid.engagement_to)}"


def _engagement_days(bid):
    return f"{bid.engagement_days}d" if bid.engagement_days is not None else "—"


def _management_cost_cell(bid):
    bdt = getattr(bid, "management_cost_bdt", None)
    usd = getattr(bid, "management_cost_usd", None)
    if bdt is None:
        return "—"
    text = f"৳{bdt:,.2f}"
    return f"{text} · ${usd:,.2f}" if usd else text


@dataclass
class ExportColumn:
    key: str
    label: str
    group: str
    default_visible: bool
    value: Callable[[Bid], str]
    is_new: bool = False


COLUMNS = [
    ExportColumn("serial", "SL", "Core", True, lambda b: str(b.serial) if getattr(b, "serial", None) is not None else "—"),
    ExportColumn("client", "Client", "Core", True, lambda b: b.client.name),
    ExportColumn("description", "Description", "Core", False, lambda b: b.description or "—"),
    ExportColumn("team", "Team", "New fields", True, lambda b: b.team.name if b.team else "—", is_new=True),
    ExportColumn("stage", "Stage", "Core", True, lambda b: b.stage or "—"),
    ExportColumn("procurement_type", "Procurement type", "Core", False, lambda b: b.procurement_type or "—"),
    ExportColumn("initiation_mode", "Initiation mode", "Core", False, lambda b: b.initiation_mode or "—"),
    ExportColumn("delivery_type", "Delivery type", "Core", False, _delivery_type),
    ExportColumn("tender_id", "Tender ID", "Core", False, lambda b: b.tender_id or "—"),
    ExportColumn("cam", "CAM", "People", False, lambda b: _name_or_dash(b.cam)),
    ExportColumn("sales_resource", "Sales resource", "People", False, lambda b: _name_or_dash(b.sales_resource)),
    ExportColumn("bid_manager", "Bid manager", "People", True, lambda b: _name_or_dash(b.bid_manager)),
    ExportColumn("engaged_resources", "Engaged resources", "New fields", True, _engaged_resources, is_new=True),
    ExportColumn("engagement_period", "Engagement period", "New fields", False, _engagement_period, is_new=True),
    ExportColumn("engagement_days", "Engagement days", "New fields", False, _engagement_days, is_new=True),
    ExportColumn("initiation_date", "Initiation date", "Dates", False, lambda b: _dmy(b.initiation_date)),
    ExportColumn("published_date", "Published", "Dates", True, lambda b: _dmy(b.published_date)),
    ExportColumn("prebid_date", "Pre-bid", "Dates", False, lambda b: _date_time_cell(b.prebid_date, b.prebid_time)),
    ExportColumn("submission_date", "Submission", "Dates", True, lambda b: _date_time_cell(b.submission_date, b.submission_time)),
    ExportColumn("security_mode", "Security mode", "Financial", False, lambda b: b.security_mode or "—"),
    ExportColumn("security_amount", "Security amount", "Financial", False, lambda b: _money_cell(b.security_amount_raw)),
    ExportColumn("credit_facility", "Credit facility", "Financial", False, lambda b: _money_cell(b.credit_facility_raw)),
    # §Phase 22 item 3 — summary figure only (queryset-annotated, see
    # filtered_export_queryset's with_management_cost() call); the full
    # breakdown lives on the bid's own detail page and its PDF.
    ExportColumn("management_cost", "Management cost", "Financial", False, _management_cost_cell),
    ExportColumn("bg_issue_date", "BG issue date", "Financial", False, lambda b: _dmy(b.bg_issue_date)),
    ExportColumn("bg_reference", "BG / reference no.", "Financial", False, lambda b: b.bg_reference or "—"),
    ExportColumn("bg_bank", "Issuing bank", "Financial", False, lambda b: b.bg_bank or "—"),
    ExportColumn("bg_expiry_date", "BG expiry", "Dates", True, lambda b: _dmy(b.bg_expiry_date)),
    ExportColumn("submission_status", "Submission status", "Status", True, lambda b: b.submission_status or "—"),
    ExportColumn("result", "Result", "Status", True, lambda b: b.result or "—"),
    ExportColumn("remarks", "Remarks", "Core", False, lambda b: b.remarks or "—"),
]

COLUMNS_BY_KEY = {c.key: c for c in COLUMNS}
DEFAULT_VISIBLE_KEYS = [c.key for c in COLUMNS if c.default_visible]


def resolve_columns(requested_keys):
    """Returns an ordered list of ExportColumn for the requested keys,
    falling back to the register's own default set (§13) if none/invalid
    were given — an export should never silently produce zero columns."""
    if requested_keys:
        columns = [COLUMNS_BY_KEY[k] for k in requested_keys if k in COLUMNS_BY_KEY]
        if columns:
            return columns
    return [COLUMNS_BY_KEY[k] for k in DEFAULT_VISIBLE_KEYS]
