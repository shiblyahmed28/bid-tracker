"""§Phase 23 — append-only sheet write-back. Besides the uid backfill (§6),
this is the only other write the app ever makes to the sheet, and it only
ever adds a brand-new row — never rewrites or deletes an existing one.

Admin-gated (SheetAppendSettings, default OFF) and checked both by the
caller and again inside append_bid_to_sheet itself, so the gate holds
regardless of what triggers a call: the create-bid request or the periodic
retry sweep.
"""

import re
import uuid

from apps.audit.models import AuditEntry

from . import columns
from .sheets_client import HEADER_ROW, find_column_index, get_worksheet

APPENDED_RANGE_RE = re.compile(r"![A-Z]+(\d+):[A-Z]+(\d+)")


class SheetAppendDisabledError(Exception):
    pass


def _iso_date(value):
    return value.strftime("%Y-%m-%d") if value else ""


def _iso_time(value):
    return value.strftime("%H:%M:%S") if value else ""


def build_append_row(bid, width, uid_col_index, remarks_col_index):
    """One row of plain text, addressed by the same fixed column indices as
    the read side (apps/sync/columns.py, §5) — every value is written in the
    exact format normalizers.py round-trips back to the identical value, so
    the very next sync sees no diff on this row and raises no spurious
    SyncConflict. team / engaged_resources / engagement dates / BidCostLine
    are app-native (§7) — the sheet has no column for any of them, so none
    is ever written here."""
    row = [""] * width

    def put(index, value):
        if index is not None and 0 <= index < width:
            row[index] = value

    put(columns.CLIENT, bid.client.name)
    put(columns.DESCRIPTION, bid.description)
    put(columns.CAM, bid.cam.canonical_name if bid.cam else "")
    put(columns.SALES_RESOURCE, bid.sales_resource.canonical_name if bid.sales_resource else "")
    put(columns.BID_MANAGER, bid.bid_manager.canonical_name if bid.bid_manager else "")
    put(columns.INITIATION_MODE, bid.initiation_mode)
    put(columns.STAGE, bid.stage)
    put(columns.PROCUREMENT_TYPE, bid.procurement_type)
    put(columns.GOODS, "Goods" if bid.is_goods else "")
    put(columns.WORKS, "Works" if bid.is_works else "")
    put(columns.SERVICE, "Service" if bid.is_service else "")
    put(columns.TENDER_ID, bid.tender_id)
    put(columns.INITIATION_DATE, _iso_date(bid.initiation_date))
    put(columns.PUBLISHED_DATE, _iso_date(bid.published_date))
    put(columns.PREBID_DATE, _iso_date(bid.prebid_date))
    put(columns.PREBID_TIME, _iso_time(bid.prebid_time))
    put(columns.SUBMISSION_DATE, _iso_date(bid.submission_date))
    put(columns.SUBMISSION_TIME, _iso_time(bid.submission_time))
    put(columns.SECURITY_MODE, bid.security_mode)
    put(columns.SECURITY_AMOUNT, bid.security_amount_raw)
    put(columns.CREDIT_FACILITY, bid.credit_facility_raw)
    put(columns.BG_ISSUE_DATE, _iso_date(bid.bg_issue_date))
    put(columns.BG_REFERENCE, bid.bg_reference)
    put(columns.BG_BANK, bid.bg_bank)
    put(columns.BG_EXPIRY_DATE, _iso_date(bid.bg_expiry_date))
    put(columns.SUBMISSION_STATUS, bid.submission_status)
    put(columns.RESULT, bid.result)
    put(remarks_col_index, bid.remarks)
    put(uid_col_index, str(bid.uid))

    return row


def _parse_appended_row_number(response):
    updated_range = (response or {}).get("updates", {}).get("updatedRange", "")
    match = APPENDED_RANGE_RE.search(updated_range)
    if not match:
        raise ValueError(f"Could not determine the appended row number from {updated_range!r}")
    return int(match.group(1))


def append_bid_to_sheet(bid):
    """Appends one row for `bid` to the bids worksheet and records the
    resulting sheet row number (§23 rule 6: "every append writes an audit
    entry with the sheet row number"). One append_row call — never a rewrite
    of any existing row (§23 rules 1/3). Raises on any failure; the caller is
    responsible for catching it, recording the error, and leaving the bid
    flagged pending_sheet_append for the next retry."""
    from apps.settings_admin.models import SheetAppendSettings

    if not SheetAppendSettings.load().enabled:
        raise SheetAppendDisabledError("Sheet append is turned off. An admin must enable it first.")

    if bid.uid is None:
        bid.uid = uuid.uuid4()

    worksheet = get_worksheet()
    header_row = worksheet.row_values(HEADER_ROW)

    uid_col_index = find_column_index(header_row, "uid")
    if uid_col_index is None:
        raise ValueError("No 'uid' column found on the header row (row 3). Refusing to append.")

    remarks_col_index = find_column_index(header_row, "remarks")
    if remarks_col_index is None:
        remarks_col_index = columns.REMARKS_FALLBACK

    width = max(len(header_row), uid_col_index + 1, remarks_col_index + 1)
    row = build_append_row(bid, width, uid_col_index, remarks_col_index)

    response = worksheet.append_row(row, value_input_option="RAW", insert_data_option="INSERT_ROWS")
    row_number = _parse_appended_row_number(response)

    bid.sheet_row = row_number
    bid.pending_sheet_append = False
    bid.sheet_append_error = ""
    bid.save(update_fields=["uid", "sheet_row", "pending_sheet_append", "sheet_append_error"])

    AuditEntry.objects.create(
        actor=None,
        actor_label="System (sheet append)",
        action=AuditEntry.Action.SHEET_APPEND,
        bid=bid,
        field="sheet_row",
        new_value=str(row_number),
    )
    return row_number


def queue_bid_for_sheet_append(bid):
    """Called right after a bid is created in the app (§23). A complete
    no-op while the feature is off — nothing is flagged, nothing is written
    (§23: "disabled means no write occurs"). When on, the append is
    attempted immediately; any failure is caught here so it can never block
    bid creation (§23 rule 4) — the bid stays flagged pending_sheet_append
    with the error recorded, and the periodic retry sweep
    (retry_pending_sheet_appends, Celery Beat) picks it up later."""
    from apps.settings_admin.models import SheetAppendSettings

    if not SheetAppendSettings.load().enabled:
        return

    bid.pending_sheet_append = True
    bid.save(update_fields=["pending_sheet_append"])

    try:
        append_bid_to_sheet(bid)
    except Exception as exc:
        bid.sheet_append_error = str(exc)
        bid.save(update_fields=["sheet_append_error"])


def retry_pending_sheet_appends():
    """Re-attempts every bid still flagged pending (§23: "queue for retry")
    — run on its own Beat schedule so a transient failure (API hiccup,
    expired credentials, rate limit) doesn't get stuck forever once the
    underlying problem clears. Each bid fails or succeeds independently."""
    from apps.bids.models import Bid

    for bid in Bid.objects.filter(source=Bid.Source.APP, pending_sheet_append=True):
        try:
            append_bid_to_sheet(bid)
        except SheetAppendDisabledError:
            # Turned off again after being queued — leave it pending as-is;
            # the next sweep will retry once an admin re-enables it.
            continue
        except Exception as exc:
            bid.sheet_append_error = str(exc)
            bid.save(update_fields=["sheet_append_error"])
