import base64
import csv
import itertools

from celery.result import AsyncResult
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settings_admin.capabilities import HasCapability

from .export_columns import resolve_columns
from .export_filters import describe_filters, filtered_export_queryset
from .models import Bid
from .pdf import render_bid_register_pdf
from .tasks import generate_bid_register_pdf_task

SELECT_RELATED = ("client", "cam", "sales_resource", "bid_manager", "team", "created_by", "updated_by")
PREFETCH_RELATED = ("engaged_resources",)

# §13 bullet 5: over this many rows, WeasyPrint runs in a Celery task
# instead of blocking the request.
ROW_THRESHOLD_FOR_ASYNC = 500


def _base_queryset():
    return Bid.objects.select_related(*SELECT_RELATED).prefetch_related(*PREFETCH_RELATED).with_serial()


def _requested_columns(request):
    keys = [k for k in request.query_params.get("columns", "").split(",") if k]
    return resolve_columns(keys)


def _generated_by_label(user):
    return user.full_name or user.email


def _pdf_filename():
    return f"bid-register-{timezone.localdate().isoformat()}.pdf"


class BidExportPdfView(APIView):
    """GET /bids/export/pdf/ — same filters as /bids/, plus columns= (§13).
    Synchronous under the row threshold; otherwise kicks off a Celery task
    and returns 202 with a task_id for BidExportPdfStatusView/DownloadView."""

    permission_classes = [HasCapability("export_pdf")]

    def get(self, request):
        queryset = filtered_export_queryset(_base_queryset(), request.query_params)
        row_count = queryset.count()

        if row_count > ROW_THRESHOLD_FOR_ASYNC:
            params = dict(request.query_params.items())
            task = generate_bid_register_pdf_task.delay(params, _generated_by_label(request.user))
            return Response({"task_id": task.id, "row_count": row_count}, status=status.HTTP_202_ACCEPTED)

        columns = _requested_columns(request)
        filters_caption = describe_filters(request.query_params)
        pdf_bytes = render_bid_register_pdf(queryset, columns, filters_caption, _generated_by_label(request.user))

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{_pdf_filename()}"'
        return response


class BidExportPdfStatusView(APIView):
    """GET /bids/export/pdf/status/?task_id=... — polled by the frontend
    while an async export is running."""

    permission_classes = [HasCapability("export_pdf")]

    def get(self, request):
        task_id = request.query_params.get("task_id")
        if not task_id:
            return Response({"detail": "task_id is required."}, status=400)
        result = AsyncResult(task_id)
        return Response({"task_id": task_id, "state": result.state})


class BidExportPdfDownloadView(APIView):
    """GET /bids/export/pdf/download/?task_id=... — only serves once the
    task has succeeded; the frontend calls this after status polling."""

    permission_classes = [HasCapability("export_pdf")]

    def get(self, request):
        task_id = request.query_params.get("task_id")
        if not task_id:
            return Response({"detail": "task_id is required."}, status=400)

        result = AsyncResult(task_id)
        if not result.ready():
            return Response({"detail": "Export is not ready yet.", "state": result.state}, status=409)
        if result.failed():
            return Response({"detail": "Export failed."}, status=500)

        payload = result.get()
        pdf_bytes = base64.b64decode(payload["pdf_base64"])
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{payload["filename"]}"'
        return response


class _Echo:
    """A file-like object whose write() hands back what it was given,
    letting csv.writer drive a generator instead of buffering in memory."""

    def write(self, value):
        return value


class BidExportCsvView(APIView):
    """GET /bids/export/csv/ — same filters as /bids/, plus columns=.
    Always synchronous and streamed (§13 bullet 6) — CSV generation is cheap
    even for the full register, unlike WeasyPrint rendering."""

    permission_classes = [HasCapability("export_pdf")]

    def get(self, request):
        queryset = filtered_export_queryset(_base_queryset(), request.query_params)
        columns = _requested_columns(request)

        def rows():
            yield [c.label for c in columns]
            for bid in queryset.iterator(chunk_size=200):
                yield [c.value(bid) for c in columns]

        writer = csv.writer(_Echo())
        # A leading BOM is what makes Excel — the most common consumer of
        # this file — auto-detect UTF-8 instead of misreading the "—" and
        # similar characters that show up throughout the sheet data.
        streaming_rows = itertools.chain(["﻿"], (writer.writerow(row) for row in rows()))

        filename = f"bid-register-{timezone.localdate().isoformat()}.csv"
        response = StreamingHttpResponse(streaming_rows, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
