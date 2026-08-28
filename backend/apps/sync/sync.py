"""The sync algorithm, §9 step for step. Match on uid only — never tender-id,
never row position (§6). A row that fails to parse quarantines and the run
continues; nothing here may let one bad row abort the sync (§9.5, §20).
"""

import uuid
from collections import Counter

from django.db import transaction

from apps.audit.models import AuditEntry
from apps.bids.models import Bid
from apps.sync.models import QuarantineRow, SyncConflict, SyncRun

from . import columns
from .normalizers import norm_delivery_type, norm_date, norm_enum, norm_money, norm_person, norm_text, norm_time
from .resolvers import resolve_client, resolve_person
from .sheets_client import HEADER_ROW, find_column_index, get_client, get_worksheet, read_data_rows
from .uid_backfill import apply_uid_backfill, compute_uid_backfill

# Keys in normalize_row()'s output that need Person/Client resolution before
# they can be assigned to a Bid — excluded from the direct field-name mapping.
RESOLVED_KEYS = {"client_name", "cam_name", "sales_resource_name", "bid_manager_name"}

CRITICAL_FIELD_MISSING = "Missing client or usable submission date"


def normalize_row(row, remarks_col_index):
    """Returns a dict keyed by Bid field name (plus the four *_name keys that
    still need Person/Client resolution). Never raises — every sub-value that
    fails to parse becomes None/blank, per §8."""
    is_goods, is_works, is_service = norm_delivery_type(
        columns.cell(row, columns.GOODS),
        columns.cell(row, columns.WORKS),
        columns.cell(row, columns.SERVICE),
    )
    security_raw, security_amount, security_currency = norm_money(columns.cell(row, columns.SECURITY_AMOUNT))
    credit_raw, credit_amount, credit_currency = norm_money(columns.cell(row, columns.CREDIT_FACILITY))

    return {
        "client_name": norm_text(columns.cell(row, columns.CLIENT)),
        "description": norm_text(columns.cell(row, columns.DESCRIPTION)) or "",
        "cam_name": norm_person(columns.cell(row, columns.CAM)),
        "sales_resource_name": norm_person(columns.cell(row, columns.SALES_RESOURCE)),
        "bid_manager_name": norm_person(columns.cell(row, columns.BID_MANAGER)),
        "initiation_mode": norm_enum(columns.cell(row, columns.INITIATION_MODE)) or "",
        "stage": norm_enum(columns.cell(row, columns.STAGE)) or "",
        "procurement_type": norm_enum(columns.cell(row, columns.PROCUREMENT_TYPE)) or "",
        "is_goods": is_goods,
        "is_works": is_works,
        "is_service": is_service,
        "tender_id": norm_text(columns.cell(row, columns.TENDER_ID)) or "",
        "initiation_date": norm_date(columns.cell(row, columns.INITIATION_DATE)),
        "published_date": norm_date(columns.cell(row, columns.PUBLISHED_DATE)),
        "prebid_date": norm_date(columns.cell(row, columns.PREBID_DATE)),
        "prebid_time": norm_time(columns.cell(row, columns.PREBID_TIME)),
        "submission_date": norm_date(columns.cell(row, columns.SUBMISSION_DATE)),
        "submission_time": norm_time(columns.cell(row, columns.SUBMISSION_TIME)),
        "submission_status": norm_enum(columns.cell(row, columns.SUBMISSION_STATUS)) or "",
        "result": norm_enum(columns.cell(row, columns.RESULT)) or "",
        "security_mode": norm_enum(columns.cell(row, columns.SECURITY_MODE)) or "",
        "security_amount_raw": security_raw,
        "security_amount": security_amount,
        "security_currency": security_currency,
        "credit_facility_raw": credit_raw,
        "credit_facility": credit_amount,
        "credit_facility_currency": credit_currency,
        "bg_issue_date": norm_date(columns.cell(row, columns.BG_ISSUE_DATE)),
        "bg_reference": norm_text(columns.cell(row, columns.BG_REFERENCE)) or "",
        "bg_bank": norm_text(columns.cell(row, columns.BG_BANK)) or "",
        "bg_expiry_date": norm_date(columns.cell(row, columns.BG_EXPIRY_DATE)),
        "remarks": norm_text(columns.cell(row, remarks_col_index)) or "",
    }


def run_sync(trigger, actor=None, dry_run=False):
    """Returns (sync_run, counts). For a dry run, sync_run is fully populated
    in memory but every write — SyncRun, Bid, Person, Client, QuarantineRow,
    SyncConflict, AuditEntry, and the sheet's uid backfill — is rolled back
    or skipped, per "writes nothing" (Phase 5 acceptance)."""
    counts = Counter()

    gc = get_client()
    worksheet = get_worksheet(gc)
    header_row = worksheet.row_values(HEADER_ROW)
    rows = read_data_rows(worksheet)

    remarks_col_index = find_column_index(header_row, "remarks")
    if remarks_col_index is None:
        remarks_col_index = columns.REMARKS_FALLBACK

    uid_col_index, backfill_updates, uid_by_row = compute_uid_backfill(header_row, rows)
    if not dry_run and backfill_updates:
        apply_uid_backfill(worksheet, uid_col_index, backfill_updates)

    person_cache = {}
    client_cache = {}
    seen_uids = set()

    with transaction.atomic():
        sync_run = SyncRun.objects.create(trigger=trigger, actor=actor)

        for row_number, row in rows:
            counts["read"] += 1
            fields = normalize_row(row, remarks_col_index)

            if fields["client_name"] is None or fields["submission_date"] is None:
                counts["quarantined"] += 1
                QuarantineRow.objects.create(
                    sync_run=sync_run,
                    sheet_row=row_number,
                    raw_data={"row": row},
                    reason=CRITICAL_FIELD_MISSING,
                )
                continue

            uid_str = uid_by_row[row_number]
            try:
                uid_value = uuid.UUID(uid_str)
            except ValueError:
                counts["quarantined"] += 1
                QuarantineRow.objects.create(
                    sync_run=sync_run,
                    sheet_row=row_number,
                    raw_data={"row": row},
                    reason=f"Invalid uid: {uid_str!r}",
                )
                continue

            seen_uids.add(uid_value)

            client_obj = resolve_client(client_cache, fields["client_name"])
            cam = resolve_person(person_cache, fields["cam_name"])
            sales_resource = resolve_person(person_cache, fields["sales_resource_name"])
            bid_manager = resolve_person(person_cache, fields["bid_manager_name"])

            sheet_values = {k: v for k, v in fields.items() if k not in RESOLVED_KEYS}
            sheet_values.update(
                client=client_obj, cam=cam, sales_resource=sales_resource, bid_manager=bid_manager
            )

            bid = Bid.all_objects.filter(uid=uid_value).first()

            if bid is None:
                counts["created"] += 1
                new_bid = Bid.objects.create(
                    uid=uid_value, source=Bid.Source.SHEET, sheet_row=row_number, **sheet_values
                )
                AuditEntry.objects.create(
                    actor=None,
                    actor_label="System (sync)",
                    action=AuditEntry.Action.BID_CREATE,
                    bid=new_bid,
                )
                continue

            bid.missing_from_sheet = False
            bid.sheet_row = row_number

            changed_any = False
            row_conflicted = False

            for field_name, new_value in sheet_values.items():
                current_value = getattr(bid, field_name)
                if current_value == new_value:
                    continue

                if field_name in bid.locally_overridden:
                    row_conflicted = True
                    SyncConflict.objects.create(
                        sync_run=sync_run,
                        bid=bid,
                        field=field_name,
                        sheet_value="" if new_value is None else str(new_value),
                        local_value="" if current_value is None else str(current_value),
                        local_editor=bid.updated_by,
                        local_edited_at=bid.updated_at,
                    )
                    continue

                bid.apply_change(field_name, new_value, actor=None)
                changed_any = True

            bid.save(update_fields=["missing_from_sheet", "sheet_row"])

            if row_conflicted:
                counts["conflicted"] += 1
            if changed_any:
                counts["updated"] += 1

        vanished = Bid.all_objects.filter(source=Bid.Source.SHEET, missing_from_sheet=False).exclude(
            uid__in=seen_uids
        )
        vanished.update(missing_from_sheet=True)

        sync_run.rows_read = counts["read"]
        sync_run.rows_created = counts["created"]
        sync_run.rows_updated = counts["updated"]
        sync_run.rows_conflicted = counts["conflicted"]
        sync_run.rows_quarantined = counts["quarantined"]
        sync_run.close(status=SyncRun.Status.SUCCESS)

        if dry_run:
            transaction.set_rollback(True)

    return sync_run, dict(counts)
