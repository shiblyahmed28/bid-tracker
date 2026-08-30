"""§Phase 23 — append-only sheet write-back. Admin-gated, default off.

Covers exactly the phase's own acceptance test list: appending then syncing
doesn't create a duplicate; a failed append doesn't block bid creation;
disabled means no write occurs at all. Sheet I/O is mocked throughout, same
pattern as test_sync_app_native_fields.py — no real Google Sheets access.
"""

import uuid
from decimal import Decimal

import pytest

from apps.audit.models import AuditEntry
from apps.bids.models import Bid
from apps.settings_admin.models import SheetAppendSettings
from apps.sync.append import (
    SheetAppendDisabledError,
    append_bid_to_sheet,
    queue_bid_for_sheet_append,
    retry_pending_sheet_appends,
)
from apps.sync.sync import run_sync

from conftest import login

# uid at index 29 — matches columns.REMARKS_FALLBACK's sibling test file.
HEADER_ROW = [""] * 29 + ["uid"]


class FakeWorksheet:
    """Records every append_row call; never exposes batch_update unless a
    test explicitly needs it, so an accidental uid-backfill write during the
    round-trip sync would fail loudly instead of silently passing."""

    def __init__(self, header=HEADER_ROW, start_row=580):
        self.header = header
        self.append_calls = []
        self._next_row = start_row

    def row_values(self, n):
        return self.header

    def append_row(self, row, value_input_option="RAW", insert_data_option=None, **kwargs):
        self.append_calls.append(list(row))
        row_number = self._next_row
        self._next_row += 1
        return {"updates": {"updatedRange": f"'bids'!A{row_number}:AE{row_number}"}}

    def batch_update(self, data):
        raise AssertionError("uid backfill should not run — the appended row already carries a uid")


def _enable_sheet_append():
    settings = SheetAppendSettings.load()
    settings.enabled = True
    settings.save()
    return settings


@pytest.mark.django_db
class TestDisabledMeansNoWriteOccurs:
    def test_queue_is_a_no_op_when_disabled(self, monkeypatch, make_bid):
        def _boom():
            raise AssertionError("get_worksheet must never be called while sheet append is disabled")

        monkeypatch.setattr("apps.sync.append.get_worksheet", _boom)

        bid = make_bid()
        assert bid.uid is None
        queue_bid_for_sheet_append(bid)

        bid.refresh_from_db()
        assert bid.uid is None
        assert bid.pending_sheet_append is False
        assert bid.sheet_append_error == ""

    def test_create_bid_api_does_not_write_when_disabled(self, monkeypatch, api_client, editor, client_obj):
        def _boom():
            raise AssertionError("get_worksheet must never be called while sheet append is disabled")

        monkeypatch.setattr("apps.sync.append.get_worksheet", _boom)

        login(api_client, editor, "EditorPass123!")
        response = api_client.post(
            "/api/v1/bids/",
            {"client_name": client_obj.name, "description": "x", "submission_date": "2026-09-10"},
            format="json",
        )
        assert response.status_code == 201
        bid = Bid.objects.get(id=response.data["id"])
        assert bid.uid is None
        assert bid.pending_sheet_append is False


@pytest.mark.django_db
class TestSuccessfulAppend:
    def test_append_writes_one_row_and_audits_with_row_number(self, monkeypatch, make_bid):
        _enable_sheet_append()
        fake = FakeWorksheet()
        monkeypatch.setattr("apps.sync.append.get_worksheet", lambda: fake)

        bid = make_bid()
        bid.remarks = "handled personally"
        bid.save(update_fields=["remarks"])

        queue_bid_for_sheet_append(bid)

        bid.refresh_from_db()
        assert bid.uid is not None
        assert bid.pending_sheet_append is False
        assert bid.sheet_append_error == ""
        assert bid.sheet_row == 580

        assert len(fake.append_calls) == 1
        row = fake.append_calls[0]
        assert row[1] == bid.client.name  # CLIENT column
        assert row[29] == str(bid.uid)  # uid column, found by header name
        assert row[30] == "handled personally"  # remarks, fallback index 30

        entry = AuditEntry.objects.get(bid=bid, action=AuditEntry.Action.SHEET_APPEND)
        assert entry.new_value == "580"
        assert entry.actor is None
        assert entry.actor_label == "System (sheet append)"

    def test_never_writes_app_native_fields(self, monkeypatch, make_bid):
        """team / engaged_resources / engagement dates / cost lines have no
        sheet column at all — build_append_row can only ever populate the
        29 §5 indices plus remarks, so this is really just confirming the
        row length matches the header/remarks width and nothing more."""
        _enable_sheet_append()
        fake = FakeWorksheet()
        monkeypatch.setattr("apps.sync.append.get_worksheet", lambda: fake)

        bid = make_bid()
        queue_bid_for_sheet_append(bid)

        row = fake.append_calls[0]
        assert len(row) == 31  # header width (30) vs remarks fallback (31) — the wider of the two


@pytest.mark.django_db
class TestFailedAppendDoesNotBlockCreation:
    def test_create_bid_api_succeeds_despite_append_failure(self, monkeypatch, api_client, editor, client_obj):
        _enable_sheet_append()

        def _boom():
            raise RuntimeError("Sheets API unavailable")

        monkeypatch.setattr("apps.sync.append.get_worksheet", _boom)

        login(api_client, editor, "EditorPass123!")
        response = api_client.post(
            "/api/v1/bids/",
            {"client_name": client_obj.name, "description": "x", "submission_date": "2026-09-10"},
            format="json",
        )
        assert response.status_code == 201

        bid = Bid.objects.get(id=response.data["id"])
        assert bid.pending_sheet_append is True
        assert "Sheets API unavailable" in bid.sheet_append_error
        assert bid.uid is None  # never persisted — the failure happened before the write
        assert not AuditEntry.objects.filter(bid=bid, action=AuditEntry.Action.SHEET_APPEND).exists()

    def test_retry_sweep_clears_a_previously_failed_append(self, monkeypatch, make_bid):
        _enable_sheet_append()
        bid = make_bid()
        bid.pending_sheet_append = True
        bid.sheet_append_error = "Sheets API unavailable"
        bid.save(update_fields=["pending_sheet_append", "sheet_append_error"])

        fake = FakeWorksheet()
        monkeypatch.setattr("apps.sync.append.get_worksheet", lambda: fake)

        retry_pending_sheet_appends()

        bid.refresh_from_db()
        assert bid.pending_sheet_append is False
        assert bid.sheet_append_error == ""
        assert len(fake.append_calls) == 1

    def test_retry_sweep_leaves_other_bids_alone_on_one_failure(self, monkeypatch, make_bid):
        _enable_sheet_append()
        ok_bid = make_bid()
        ok_bid.pending_sheet_append = True
        ok_bid.save(update_fields=["pending_sheet_append"])

        bad_bid = make_bid()
        bad_bid.pending_sheet_append = True
        bad_bid.save(update_fields=["pending_sheet_append"])

        fake = FakeWorksheet()
        real_append_row = fake.append_row
        calls = {"n": 0}

        def flaky_append_row(row, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("rate limited")
            return real_append_row(row, **kwargs)

        fake.append_row = flaky_append_row
        monkeypatch.setattr("apps.sync.append.get_worksheet", lambda: fake)

        retry_pending_sheet_appends()

        ok_bid.refresh_from_db()
        bad_bid.refresh_from_db()
        # Order isn't guaranteed, but exactly one of the two must have failed
        # and the other must have succeeded — neither aborts the other.
        results = {ok_bid.pending_sheet_append, bad_bid.pending_sheet_append}
        assert results == {True, False}


@pytest.mark.django_db
class TestAppendThenSyncDoesNotDuplicate:
    def test_round_trip_updates_in_place(self, monkeypatch, api_client, editor, client_obj):
        _enable_sheet_append()
        fake = FakeWorksheet()
        monkeypatch.setattr("apps.sync.append.get_worksheet", lambda: fake)

        login(api_client, editor, "EditorPass123!")
        response = api_client.post(
            "/api/v1/bids/",
            {
                "client_name": client_obj.name,
                "description": "a fresh app bid",
                "submission_date": "2026-09-10",
                "stage": "RFP",
            },
            format="json",
        )
        assert response.status_code == 201
        bid = Bid.objects.get(id=response.data["id"])
        assert bid.uid is not None
        assert Bid.objects.count() == 1

        appended_row = fake.append_calls[0]

        def _install_sync_io(monkeypatch):
            monkeypatch.setattr("apps.sync.sync.get_client", lambda: object())
            monkeypatch.setattr("apps.sync.sync.get_worksheet", lambda client: fake)
            monkeypatch.setattr(
                "apps.sync.sync.read_data_rows", lambda worksheet: [(bid.sheet_row, appended_row)]
            )

        _install_sync_io(monkeypatch)

        sync_run, counts = run_sync(trigger="manual")

        assert Bid.objects.count() == 1  # no duplicate created
        assert counts.get("created", 0) == 0
        assert counts.get("quarantined", 0) == 0

        bid.refresh_from_db()
        assert bid.missing_from_sheet is False
        assert bid.source == Bid.Source.APP  # sync never reclassifies the source
        assert not AuditEntry.objects.filter(bid=bid, field="stage").exists()  # no spurious diff/conflict


@pytest.mark.django_db
class TestAppendBidToSheetGuards:
    def test_raises_when_disabled(self, make_bid):
        bid = make_bid()
        with pytest.raises(SheetAppendDisabledError):
            append_bid_to_sheet(bid)

    def test_raises_when_no_uid_column(self, monkeypatch, make_bid):
        _enable_sheet_append()

        class NoUidWorksheet(FakeWorksheet):
            def row_values(self, n):
                return [""] * 29  # no "uid" header at all

        monkeypatch.setattr("apps.sync.append.get_worksheet", lambda: NoUidWorksheet())
        bid = make_bid()
        with pytest.raises(ValueError, match="uid"):
            append_bid_to_sheet(bid)


@pytest.mark.django_db
class TestSheetAppendSettingsView:
    def test_admin_can_toggle(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/settings/sheet-append/")
        assert response.status_code == 200
        assert response.data["enabled"] is False

        response = api_client.patch("/api/v1/settings/sheet-append/", {"enabled": True}, format="json")
        assert response.status_code == 200
        assert response.data["enabled"] is True
        assert AuditEntry.objects.filter(action=AuditEntry.Action.SHEET_APPEND_SETTINGS).exists()

    def test_editor_cannot_toggle(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.patch("/api/v1/settings/sheet-append/", {"enabled": True}, format="json")
        assert response.status_code == 403

    def test_viewer_cannot_even_read(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/settings/sheet-append/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestPendingSheetAppendListView:
    def test_admin_sees_pending_bids(self, api_client, admin_user, make_bid):
        bid = make_bid()
        bid.pending_sheet_append = True
        bid.sheet_append_error = "Sheets API unavailable"
        bid.save(update_fields=["pending_sheet_append", "sheet_append_error"])

        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/sync/pending-appends/")
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == str(bid.id)
        assert response.data["results"][0]["sheet_append_error"] == "Sheets API unavailable"

    def test_editor_cannot_view(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.get("/api/v1/sync/pending-appends/")
        assert response.status_code == 403
