import base64

from celery import shared_task
from django.utils import timezone

from .export_columns import resolve_columns
from .export_filters import describe_filters, filtered_export_queryset
from .models import Bid
from .pdf import render_bid_register_pdf

SELECT_RELATED = ("client", "cam", "sales_resource", "bid_manager", "team", "created_by", "updated_by")
PREFETCH_RELATED = ("engaged_resources",)


@shared_task
def generate_bid_register_pdf_task(query_params, generated_by_label):
    """§13 bullet 5: >500 rows renders here instead of inline, with the
    browser polling BidExportPdfStatusView then hitting BidExportPdfDownloadView.
    The result (small enough at this row count) is stored base64-encoded in
    the Celery result backend rather than needing separate file storage."""
    queryset = Bid.objects.select_related(*SELECT_RELATED).prefetch_related(*PREFETCH_RELATED).with_serial()
    queryset = filtered_export_queryset(queryset, query_params)

    column_keys = [k for k in query_params.get("columns", "").split(",") if k]
    columns = resolve_columns(column_keys)
    filters_caption = describe_filters(query_params)

    pdf_bytes = render_bid_register_pdf(queryset, columns, filters_caption, generated_by_label)

    return {
        "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        "filename": f"bid-register-{timezone.localdate().isoformat()}.pdf",
    }
