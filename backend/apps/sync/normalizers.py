"""Pure, dependency-free field normalizers (§8). None of these ever raise on
dirty input — a parse failure returns null so the caller can quarantine the
row without aborting the run. Never called with values from outside a sheet
row: every function takes a raw cell value (str, or None/empty) and returns
a normalized Python value.
"""

import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

NULL_TOKENS = {"", "-", "N/A", "NA"}

DATE_FORMATS = [
    "%a,%B %d,%Y",
    "%a, %B %d,%Y",
    "%a,%b %d,%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
]

TIME_FORMATS = [
    "%H:%M:%S",
    "%H:%M",
    "%I:%M %p",
    "%I:%M:%S %p",
]

MIN_YEAR = 2000
MAX_YEAR = 2100


def norm_text(value):
    """Strip, collapse internal whitespace runs, map blank/dash/N-A tokens to None."""
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).strip())
    if text.strip().upper() in NULL_TOKENS or text == "":
        return None
    return text


def norm_person(value):
    """People collapse to a canonical, whitespace-normalized name. Case is
    preserved here — case-insensitive matching happens at the Person lookup,
    not in the normalizer (this function has no database access)."""
    return norm_text(value)


def norm_date(value):
    """Try native datetime/date first, then the listed string formats.
    Reject any year outside 2000-2100 (row 184: "Wed, May 07, 0206")."""
    if value is None:
        return None
    if isinstance(value, datetime):
        candidate = value.date()
        return candidate if MIN_YEAR <= candidate.year <= MAX_YEAR else None
    if isinstance(value, date):
        return value if MIN_YEAR <= value.year <= MAX_YEAR else None

    text = norm_text(value)
    if text is None:
        return None

    # Real rows vary comma-spacing beyond what the listed formats spell out
    # literally (e.g. "Thu, Aug 27, 2026" has a space before the year too) —
    # try both as-is and with comma-spacing collapsed to match the formats.
    candidates_text = {text, re.sub(r"\s*,\s*", ",", text)}

    for fmt in DATE_FORMATS:
        for candidate_text in candidates_text:
            try:
                candidate = datetime.strptime(candidate_text, fmt).date()
            except ValueError:
                continue
            return candidate if MIN_YEAR <= candidate.year <= MAX_YEAR else None
    return None


def norm_time(value):
    """Sheet columns pre-bid time / submission time. Not in the §8 list of
    named normalizers, but the columns exist (§5 #17, #19) and the Bid model
    stores them, so this follows the same never-raise contract as the rest."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value

    text = norm_text(value)
    if text is None:
        return None

    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


_MONEY_STRIP_RE = re.compile(r"[^0-9.]")


def norm_money(value):
    """Three-field money contract (§8): always return (raw, Decimal|None, currency).
    Never discard the original text. Comma removal handles Bangladeshi
    grouping (9,20,000.00 -> 920000) — never use locale-aware parsing.
    Unparseable -> null amount, keep raw, no quarantine (common and benign).
    """
    if value is None:
        return "", None, ""

    raw = str(value).strip()
    if raw == "":
        return "", None, ""

    upper = raw.upper()
    currency = "USD" if "USD" in upper or "$" in raw else "BDT"

    cleaned = _MONEY_STRIP_RE.sub("", raw)
    if cleaned in ("", "."):
        return raw, None, currency

    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return raw, None, currency

    return raw, amount, currency


def norm_enum(value):
    """Uppercase and trim. Unknown values are accepted, not rejected — seed
    the dropdown from z-data, but never fail a row over an unfamiliar enum."""
    text = norm_text(value)
    if text is None:
        return None
    return text.upper()


_DELIVERY_TYPE_TOKENS = {
    "goods": "goods",
    "service": "service",
    "services": "service",
    "work": "works",
    "works": "works",
}


def norm_delivery_type(goods_value, works_value, service_value):
    """Three sheet columns (goods / works / service) collapse into three
    booleans. Any cell containing a recognized token (case-insensitive,
    singularized) counts as present; n/a and blank do not."""

    def is_present(value):
        text = norm_text(value)
        if text is None:
            return False
        return text.strip().lower() in _DELIVERY_TYPE_TOKENS

    return is_present(goods_value), is_present(works_value), is_present(service_value)
