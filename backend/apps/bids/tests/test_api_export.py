import datetime

import pytest

from apps.bids.export_columns import COLUMNS_BY_KEY, DEFAULT_VISIBLE_KEYS, resolve_columns
from apps.bids.export_filters import describe_filters, filtered_export_queryset
from apps.bids.models import Bid, Client

from conftest import login

TODAY = datetime.date.today()

PDF_URL = "/api/v1/bids/export/pdf/"
STATUS_URL = "/api/v1/bids/export/pdf/status/"
DOWNLOAD_URL = "/api/v1/bids/export/pdf/download/"
CSV_URL = "/api/v1/bids/export/csv/"

DEFAULT_RANGE = {"submission_after": "2000-01-01", "submission_before": "2100-12-31"}


class FakeAsyncResult:
    def __init__(self, state="PENDING", result=None, failed=False):
        self.state = state
        self._result = result
        self._failed = failed

    def ready(self):
        return self.state in ("SUCCESS", "FAILURE")

    def failed(self):
        return self._failed

    def get(self):
        return self._result


@pytest.mark.django_db
class TestPdfExportRoleMatrix:
    def test_viewer_can_export(self, api_client, viewer, make_bid):
        make_bid(description="x", submission_date=TODAY)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(PDF_URL, DEFAULT_RANGE)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_editor_can_export(self, api_client, editor, make_bid):
        make_bid(description="x", submission_date=TODAY)
        login(api_client, editor, "EditorPass123!")
        response = api_client.get(PDF_URL, DEFAULT_RANGE)
        assert response.status_code == 200

    def test_anonymous_gets_401(self, api_client):
        response = api_client.get(PDF_URL, DEFAULT_RANGE)
        assert response.status_code == 401


@pytest.mark.django_db
class TestPdfExportSync:
    def test_returns_valid_pdf_with_disposition(self, api_client, viewer, make_bid):
        make_bid(description="x", submission_date=TODAY)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(PDF_URL, DEFAULT_RANGE)
        assert response.status_code == 200
        assert response.content[:4] == b"%PDF"
        assert "attachment" in response["Content-Disposition"]
        assert response["Content-Disposition"].endswith('.pdf"')

    def test_empty_result_still_renders(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(PDF_URL, DEFAULT_RANGE)
        assert response.status_code == 200


@pytest.mark.django_db
class TestPdfExportAsync:
    def test_over_threshold_returns_202_with_task_id(self, api_client, viewer, make_bid, monkeypatch):
        monkeypatch.setattr("apps.bids.export_views.ROW_THRESHOLD_FOR_ASYNC", 2)
        for i in range(3):
            make_bid(description=f"bid {i}", submission_date=TODAY)

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(PDF_URL, DEFAULT_RANGE)
        assert response.status_code == 202
        assert response.data["row_count"] == 3
        assert "task_id" in response.data

    def test_status_reports_task_state(self, api_client, viewer, monkeypatch):
        monkeypatch.setattr(
            "apps.bids.export_views.AsyncResult", lambda task_id: FakeAsyncResult(state="STARTED")
        )
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(STATUS_URL, {"task_id": "fake-id"})
        assert response.status_code == 200
        assert response.data["state"] == "STARTED"

    def test_download_before_ready_is_409(self, api_client, viewer, monkeypatch):
        monkeypatch.setattr(
            "apps.bids.export_views.AsyncResult", lambda task_id: FakeAsyncResult(state="PENDING")
        )
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(DOWNLOAD_URL, {"task_id": "fake-id"})
        assert response.status_code == 409

    def test_download_after_success_streams_pdf(self, api_client, viewer, monkeypatch):
        fake_result = FakeAsyncResult(
            state="SUCCESS",
            result={"pdf_base64": "JVBERi0xLjc=", "filename": "bid-register-test.pdf"},
        )
        monkeypatch.setattr("apps.bids.export_views.AsyncResult", lambda task_id: fake_result)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(DOWNLOAD_URL, {"task_id": "fake-id"})
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert "bid-register-test.pdf" in response["Content-Disposition"]

    def test_download_after_failure_is_500(self, api_client, viewer, monkeypatch):
        monkeypatch.setattr(
            "apps.bids.export_views.AsyncResult",
            lambda task_id: FakeAsyncResult(state="FAILURE", failed=True),
        )
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(DOWNLOAD_URL, {"task_id": "fake-id"})
        assert response.status_code == 500


@pytest.mark.django_db
class TestCsvExport:
    def test_viewer_can_export(self, api_client, viewer, make_bid):
        make_bid(description="x", submission_date=TODAY, stage="TENDER")
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(CSV_URL, DEFAULT_RANGE)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv; charset=utf-8"

    def test_anonymous_gets_401(self, api_client):
        response = api_client.get(CSV_URL, DEFAULT_RANGE)
        assert response.status_code == 401

    def test_content_has_bom_header_and_rows(self, api_client, viewer, make_bid):
        make_bid(description="x", submission_date=TODAY, stage="TENDER", result="WON")
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(CSV_URL, {**DEFAULT_RANGE, "columns": "serial,client,stage,result"})
        raw = b"".join(response.streaming_content)
        assert raw.startswith("﻿".encode("utf-8"))
        text = raw.decode("utf-8-sig")
        lines = text.splitlines()
        assert lines[0] == "SL,Client,Stage,Result"
        assert lines[1] == "1,Acme Corp,TENDER,WON"

    def test_respects_filters(self, api_client, viewer, make_bid):
        other_client = Client.objects.create(name="Other Client", canonical_name="other client")
        make_bid(description="a", submission_date=TODAY, stage="TENDER")
        make_bid(description="b", submission_date=TODAY, client=other_client, stage="RFP")

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(CSV_URL, {**DEFAULT_RANGE, "stage": "TENDER"})
        raw = b"".join(response.streaming_content).decode("utf-8-sig")
        rows = raw.splitlines()
        assert len(rows) == 2  # header + one matching row
        assert "Acme Corp" in rows[1]


@pytest.mark.django_db
class TestFilteredExportQueryset:
    """Unit-level checks that the export path applies filters correctly —
    the acceptance test's "filtered to one client produces only that
    client's rows", verified precisely rather than by parsing PDF bytes."""

    def test_filters_to_one_client(self, make_bid):
        other_client = Client.objects.create(name="Other Client", canonical_name="other client")
        make_bid(description="a", submission_date=TODAY)
        make_bid(description="b", submission_date=TODAY, client=other_client)

        queryset = filtered_export_queryset(Bid.objects.with_serial(), {"client": "Acme"})
        assert queryset.count() == 1
        assert queryset.first().client.name == "Acme Corp"

    def test_search_matches_across_fields(self, make_bid):
        make_bid(description="a very particular widget", submission_date=TODAY)
        make_bid(description="something else entirely", submission_date=TODAY)

        queryset = filtered_export_queryset(Bid.objects.with_serial(), {"search": "particular"})
        assert queryset.count() == 1


class TestDescribeFilters:
    def test_no_filters_says_all_dates(self):
        caption = describe_filters({})
        assert "Dates: all" in caption

    def test_includes_date_range(self):
        caption = describe_filters({"submission_after": "2026-01-01", "submission_before": "2026-12-31"})
        assert "01 Jan 2026" in caption
        assert "31 Dec 2026" in caption

    def test_includes_search_and_column_filters(self):
        caption = describe_filters({"search": "hello", "stage": "TENDER"})
        assert 'Search: "hello"' in caption
        assert "Stage: TENDER" in caption

    @pytest.mark.django_db
    def test_team_id_resolves_to_name(self, team):
        caption = describe_filters({"team": str(team.id)})
        assert f"Team: {team.name}" in caption


class TestResolveColumns:
    def test_valid_keys_are_kept_in_order(self):
        columns = resolve_columns(["result", "client"])
        assert [c.key for c in columns] == ["result", "client"]

    def test_invalid_keys_are_dropped(self):
        columns = resolve_columns(["client", "not-a-real-column"])
        assert [c.key for c in columns] == ["client"]

    def test_empty_falls_back_to_defaults(self):
        columns = resolve_columns([])
        assert [c.key for c in columns] == DEFAULT_VISIBLE_KEYS

    def test_all_default_keys_exist(self):
        for key in DEFAULT_VISIBLE_KEYS:
            assert key in COLUMNS_BY_KEY
