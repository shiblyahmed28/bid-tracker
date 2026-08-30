"""Master Settings > Sheet sync "Reset all bid data" — an admin-only,
destructive danger-zone action: delete every Bid (app-created and
sheet-sourced alike) and resync fresh from the sheet in one step, without
the mass-notification storm a from-scratch resync would otherwise cause
(every row is "new" again). Sheet I/O mocked throughout — same pattern as
test_sync_app_native_fields.py.
"""

import uuid

import pytest

from apps.audit.models import AuditEntry
from apps.bids.models import Bid
from apps.notifications.models import Notification, SentEmail
from apps.sync.sync import run_sync

from conftest import login

HEADER_ROW = [""] * 29 + ["uid"]


def _row(uid_value, client_name="Fresh Sheet Client", submission_date="2026-09-01"):
    row = [""] * 30
    row[1] = client_name
    row[2] = "a description"
    row[7] = "RFP"
    row[18] = submission_date
    row[29] = uid_value
    return row


class FakeWorksheet:
    def __init__(self, rows):
        self._rows = rows

    def row_values(self, n):
        return HEADER_ROW

    def batch_update(self, data):
        raise AssertionError("uid backfill should not run — every row already has a uid")


@pytest.fixture
def fake_sheet_io(monkeypatch):
    def _install(sheet_rows):
        monkeypatch.setattr("apps.sync.sync.get_client", lambda: object())
        monkeypatch.setattr("apps.sync.sync.get_worksheet", lambda client: FakeWorksheet(sheet_rows))
        monkeypatch.setattr("apps.sync.sync.read_data_rows", lambda worksheet: sheet_rows)

    return _install


@pytest.mark.django_db
class TestRunSyncNotifyFlag:
    def test_notify_false_suppresses_new_bid_email(self, fake_sheet_io, client_obj):
        fake_sheet_io([(4, _row(str(uuid.uuid4())))])
        run_sync(trigger="manual", notify=False)
        assert Notification.objects.count() == 0
        assert SentEmail.objects.count() == 0

    def test_notify_true_is_the_default_and_unchanged(self, fake_sheet_io, client_obj, viewer):
        """Not asserting an email actually sends (SMTP isn't mocked here) —
        just that the notify=True default still reaches notify_new_bid,
        which always writes the in-app Notification row first."""
        fake_sheet_io([(4, _row(str(uuid.uuid4())))])
        run_sync(trigger="manual")
        assert Notification.objects.filter(kind=Notification.Kind.NEW_BID).exists()


@pytest.mark.django_db
class TestSyncResetView:
    def test_admin_resets_deleting_old_data_and_resyncing(
        self, api_client, admin_user, fake_sheet_io, make_bid
    ):
        stale_app_bid = make_bid()
        stale_sheet_bid = make_bid(uid=uuid.uuid4(), source=Bid.Source.SHEET)

        fresh_uid = str(uuid.uuid4())
        fake_sheet_io([(4, _row(fresh_uid, client_name="Civil Aviation Authority"))])

        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/sync/reset/", {"confirm": True}, format="json")

        assert response.status_code == 200
        assert response.data["deleted"] == 2
        assert response.data["sync_run"]["rows_created"] == 1

        assert not Bid.all_objects.filter(pk=stale_app_bid.pk).exists()
        assert not Bid.all_objects.filter(pk=stale_sheet_bid.pk).exists()

        remaining = Bid.objects.get()
        assert str(remaining.uid) == fresh_uid
        assert remaining.client.name == "Civil Aviation Authority"

    def test_reset_sends_no_notifications_despite_every_row_being_new(
        self, api_client, admin_user, fake_sheet_io, make_bid
    ):
        make_bid()  # stale data to be wiped
        fake_sheet_io([(4, _row(str(uuid.uuid4())))])

        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/sync/reset/", {"confirm": True}, format="json")

        assert response.status_code == 200
        assert Notification.objects.count() == 0
        assert SentEmail.objects.count() == 0

    def test_writes_an_audit_entry_with_deleted_and_created_counts(
        self, api_client, admin_user, fake_sheet_io, make_bid
    ):
        make_bid()
        make_bid()
        fake_sheet_io([(4, _row(str(uuid.uuid4())))])

        login(api_client, admin_user, "AdminPass123!")
        api_client.post("/api/v1/sync/reset/", {"confirm": True}, format="json")

        entry = AuditEntry.objects.get(action=AuditEntry.Action.BID_DATA_RESET)
        assert entry.old_value == "2"
        assert entry.new_value == "1"
        assert entry.actor == admin_user

    def test_requires_explicit_confirm(self, api_client, admin_user, fake_sheet_io, make_bid):
        bid = make_bid()
        fake_sheet_io([(4, _row(str(uuid.uuid4())))])

        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/sync/reset/", {}, format="json")

        assert response.status_code == 400
        assert Bid.all_objects.filter(pk=bid.pk).exists()  # nothing was touched

    def test_editor_gets_403(self, api_client, editor, fake_sheet_io):
        fake_sheet_io([(4, _row(str(uuid.uuid4())))])
        login(api_client, editor, "EditorPass123!")
        response = api_client.post("/api/v1/sync/reset/", {"confirm": True}, format="json")
        assert response.status_code == 403

    def test_viewer_gets_403(self, api_client, viewer, fake_sheet_io):
        fake_sheet_io([(4, _row(str(uuid.uuid4())))])
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.post("/api/v1/sync/reset/", {"confirm": True}, format="json")
        assert response.status_code == 403

    def test_a_failed_sync_rolls_back_the_delete_too(self, api_client, admin_user, monkeypatch, make_bid):
        """If the resync half fails, the reset must not leave the database
        deleted-but-not-rebuilt — the whole thing is one transaction."""
        bid = make_bid()

        def _boom():
            raise RuntimeError("Sheets API unavailable")

        monkeypatch.setattr("apps.sync.sync.get_client", _boom)

        login(api_client, admin_user, "AdminPass123!")
        with pytest.raises(RuntimeError):
            api_client.post("/api/v1/sync/reset/", {"confirm": True}, format="json")

        assert Bid.all_objects.filter(pk=bid.pk).exists()
