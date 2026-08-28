"""gspread wrapper — the only module that talks to Google Sheets. Header is
on row 3, data starts on row 4 (§5). Scoped to spreadsheets only (not full
Drive access), matching the "narrow write" non-negotiable (§2.3).
"""

import gspread
from django.conf import settings
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADER_ROW = 3
DATA_START_ROW = 4


def get_client():
    credentials = Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return gspread.authorize(credentials)


def get_worksheet(client=None):
    client = client or get_client()
    spreadsheet = client.open_by_key(settings.GOOGLE_SHEET_ID)
    return spreadsheet.worksheet(settings.GOOGLE_SHEET_TAB)


def read_header(worksheet):
    return worksheet.row_values(HEADER_ROW)


def read_data_rows(worksheet):
    """One Sheets API call for the whole tab. Returns a list of
    (sheet_row_number, padded_row_values) — blank trailing rows dropped, and
    every row padded to the header's width since the API trims each row to
    its own last non-empty cell rather than to a common width."""
    all_values = worksheet.get_all_values()
    header = all_values[HEADER_ROW - 1] if len(all_values) >= HEADER_ROW else []
    width = len(header)

    rows = []
    for offset, row in enumerate(all_values[DATA_START_ROW - 1:]):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) < width:
            row = row + [""] * (width - len(row))
        rows.append((DATA_START_ROW + offset, row))
    return rows


def find_column_index(header_row, name):
    target = name.strip().lower()
    for index, header in enumerate(header_row):
        if header.strip().lower() == target:
            return index
    return None


def find_uid_column_index(header_row):
    return find_column_index(header_row, "uid")
