"""§6: the only write the app ever makes to the sheet — the uid column,
batched into one call. Never written cell by cell (rate limits)."""

import uuid

import gspread

from .sheets_client import find_uid_column_index


def compute_uid_backfill(header_row, rows):
    """rows: list of (sheet_row_number, padded_row_values) from read_data_rows.
    Returns (uid_col_index, updates, uid_by_row):
      - updates: [{"row": n, "uid": "<new uuid4>"}] for rows with a blank uid cell
      - uid_by_row: {row_number: uid_string} for every row, existing or newly minted
    Raises if the sheet has no 'uid' header — that's a structural problem with
    the sheet itself, not a bad row, so it must not be swallowed into quarantine.
    """
    uid_col_index = find_uid_column_index(header_row)
    if uid_col_index is None:
        raise ValueError("No 'uid' column found on the header row (row 3). Refusing to sync.")

    updates = []
    uid_by_row = {}
    for row_number, row in rows:
        existing = row[uid_col_index].strip() if uid_col_index < len(row) else ""
        if existing:
            uid_by_row[row_number] = existing
        else:
            new_uid = str(uuid.uuid4())
            uid_by_row[row_number] = new_uid
            updates.append({"row": row_number, "uid": new_uid})

    return uid_col_index, updates, uid_by_row


def apply_uid_backfill(worksheet, uid_col_index, updates):
    if not updates:
        return

    a1 = gspread.utils.rowcol_to_a1(1, uid_col_index + 1)
    col_letters = "".join(ch for ch in a1 if ch.isalpha())

    data = [
        {"range": f"{col_letters}{item['row']}", "values": [[item["uid"]]]}
        for item in updates
    ]
    worksheet.batch_update(data)
