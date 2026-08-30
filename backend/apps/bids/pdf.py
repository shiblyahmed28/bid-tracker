import base64
from pathlib import Path

from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

LOGO_PATH = Path(__file__).resolve().parent / "pdf_assets" / "logo.png"
_LOGO_DATA_URI = "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")

# §12/§19: store UTC, render Dhaka — the PDF's generated-at timestamp too.
TIMESTAMP_FORMAT = "%d %b %Y, %H:%M"


def build_rows(queryset, columns):
    return [[column.value(bid) for column in columns] for bid in queryset]


def render_bid_register_pdf(queryset, columns, filters_caption, generated_by_label):
    rows = build_rows(queryset, columns)
    generated_at = timezone.localtime().strftime(TIMESTAMP_FORMAT) + " (Asia/Dhaka)"

    html_string = render_to_string(
        "bids/export_pdf.html",
        {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "filters_caption": filters_caption,
            "generated_by": generated_by_label,
            "generated_at": generated_at,
            "logo_data_uri": _LOGO_DATA_URI,
        },
    )
    return HTML(string=html_string).write_pdf()


def render_bid_detail_pdf(bid):
    """§Phase 22 item 3 — the one place besides the detail page itself that
    carries the *full* cost breakdown (register/dashboard only ever get the
    summary figure). `bid` should already have engagements__person and
    cost_lines prefetched by the caller."""
    generated_at = timezone.localtime().strftime(TIMESTAMP_FORMAT) + " (Asia/Dhaka)"

    html_string = render_to_string(
        "bids/detail_pdf.html",
        {
            "bid": bid,
            "engagements": bid.engagements.all(),
            "cost_lines": bid.cost_lines.with_line_number(),
            "generated_at": generated_at,
            "logo_data_uri": _LOGO_DATA_URI,
        },
    )
    return HTML(string=html_string).write_pdf()
