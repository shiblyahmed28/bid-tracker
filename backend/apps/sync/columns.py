"""Sheet column indices (§5), 0-indexed as they appear on row 3.

Address every column by index, never by name — two columns are both named
"submission" (18 is the deadline date, 27 is the Submitted/Not Submitted
enum), one header contains a newline, and one (14) is a stray annotation.
`uid` is the sole exception: it is looked up by header text at sync time
because it's the one unambiguous, unique header name, added far to the right.
"""

CLIENT = 1
DESCRIPTION = 2
CAM = 3
SALES_RESOURCE = 4
BID_MANAGER = 5
INITIATION_MODE = 6
STAGE = 7
PROCUREMENT_TYPE = 8
GOODS = 9
WORKS = 10
SERVICE = 11
TENDER_ID = 12
INITIATION_DATE = 13
# 14 = "published" -> "initiation" stray annotation — ignored.
PUBLISHED_DATE = 15
PREBID_DATE = 16
PREBID_TIME = 17
SUBMISSION_DATE = 18
SUBMISSION_TIME = 19
SECURITY_MODE = 20
SECURITY_AMOUNT = 21
CREDIT_FACILITY = 22
BG_ISSUE_DATE = 23
BG_REFERENCE = 24
BG_BANK = 25
BG_EXPIRY_DATE = 26
SUBMISSION_STATUS = 27  # duplicate header name "submission" — index only
RESULT = 28

# §5 documents columns 29-33 as spacer/remarks/unnamed, but the live sheet has
# drifted: it now carries extra "Engaged resource" / "Engaged Duration" /
# "Team" columns before remarks — exactly the §7 app-native fields, so this
# is prototype/demo data (§7: "do not port that seeding logic into the app")
# and is deliberately never read. `remarks` is therefore looked up by header
# name at sync time (sheets_client.find_column_index), not by fixed index,
# since its position isn't stable — this constant is a last-resort fallback
# only, kept in sync with §5's originally documented position.
REMARKS_FALLBACK = 30


def cell(row, index):
    return row[index] if index < len(row) else ""
