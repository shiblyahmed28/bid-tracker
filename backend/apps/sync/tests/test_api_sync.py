import pytest

from apps.audit.models import AuditEntry
from apps.sync.models import QuarantineRow, SyncConflict, SyncRun

from conftest import login


@pytest.fixture
def sync_run(db):
    return SyncRun.objects.create(trigger=SyncRun.Trigger.SCHEDULED, status=SyncRun.Status.SUCCESS)


@pytest.fixture
def fake_run_sync(monkeypatch, sync_run):
    """/sync/run/ shouldn't hit the real Google Sheet in tests."""

    def _fake(trigger, actor=None, dry_run=False):
        return sync_run, {"read": 0, "created": 0, "updated": 0, "conflicted": 0, "quarantined": 0}

    monkeypatch.setattr("apps.sync.views.run_sync", _fake)
    return _fake


@pytest.mark.django_db
class TestSyncRunTrigger:
    def test_viewer_gets_403(self, api_client, viewer, fake_run_sync):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.post("/api/v1/sync/run/")
        assert response.status_code == 403

    def test_editor_gets_403(self, api_client, editor, fake_run_sync):
        login(api_client, editor, "EditorPass123!")
        response = api_client.post("/api/v1/sync/run/")
        assert response.status_code == 403

    def test_admin_can_trigger(self, api_client, admin_user, fake_run_sync, sync_run):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/sync/run/")
        assert response.status_code == 201
        assert AuditEntry.objects.filter(action=AuditEntry.Action.MANUAL_SYNC_TRIGGER).exists()


@pytest.mark.django_db
class TestSyncRunsList:
    """Explicitly required by Phase 6: viewer AND editor both get 403 here."""

    def test_viewer_gets_403(self, api_client, viewer, sync_run):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/sync/runs/")
        assert response.status_code == 403

    def test_editor_gets_403(self, api_client, editor, sync_run):
        login(api_client, editor, "EditorPass123!")
        response = api_client.get("/api/v1/sync/runs/")
        assert response.status_code == 403

    def test_admin_can_list(self, api_client, admin_user, sync_run):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/sync/runs/")
        assert response.status_code == 200
        assert response.data["count"] == 1


@pytest.mark.django_db
class TestQuarantineList:
    def test_viewer_gets_403(self, api_client, viewer, sync_run):
        QuarantineRow.objects.create(sync_run=sync_run, sheet_row=4, reason="no submission date")
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/sync/quarantine/")
        assert response.status_code == 403

    def test_editor_gets_403(self, api_client, editor, sync_run):
        QuarantineRow.objects.create(sync_run=sync_run, sheet_row=4, reason="no submission date")
        login(api_client, editor, "EditorPass123!")
        response = api_client.get("/api/v1/sync/quarantine/")
        assert response.status_code == 403

    def test_admin_can_list(self, api_client, admin_user, sync_run):
        QuarantineRow.objects.create(sync_run=sync_run, sheet_row=4, reason="no submission date")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/sync/quarantine/")
        assert response.status_code == 200
        assert response.data["count"] == 1


@pytest.mark.django_db
class TestSyncConflicts:
    """§11: "resolve conflicts" is grouped with create/edit bid — editor+, not admin-only."""

    def make_conflict(self, sync_run, bid):
        return SyncConflict.objects.create(
            sync_run=sync_run,
            bid=bid,
            field="remarks",
            sheet_value="sheet says this",
            local_value="editor typed this",
        )

    def test_viewer_gets_403_on_list(self, api_client, viewer, sync_run, make_bid):
        bid = make_bid()
        self.make_conflict(sync_run, bid)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/sync/conflicts/")
        assert response.status_code == 403

    def test_editor_can_list(self, api_client, editor, sync_run, make_bid):
        bid = make_bid()
        self.make_conflict(sync_run, bid)
        login(api_client, editor, "EditorPass123!")
        response = api_client.get("/api/v1/sync/conflicts/")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_viewer_gets_403_on_resolve(self, api_client, viewer, sync_run, make_bid):
        bid = make_bid()
        conflict = self.make_conflict(sync_run, bid)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.post(f"/api/v1/sync/conflicts/{conflict.id}/resolve/", {"choose": "local"})
        assert response.status_code == 403

    def test_editor_can_resolve_keep_local(self, api_client, editor, sync_run, make_bid):
        bid = make_bid(remarks="editor typed this")
        bid.locally_overridden = ["remarks"]
        bid.save()
        conflict = self.make_conflict(sync_run, bid)

        login(api_client, editor, "EditorPass123!")
        response = api_client.post(f"/api/v1/sync/conflicts/{conflict.id}/resolve/", {"choose": "local"})
        assert response.status_code == 200

        bid.refresh_from_db()
        conflict.refresh_from_db()
        assert bid.remarks == "editor typed this"
        assert "remarks" in bid.locally_overridden
        assert conflict.resolved is True
        assert conflict.resolution == "local"
        assert conflict.resolved_by_id == editor.id
        assert AuditEntry.objects.filter(bid=bid, action=AuditEntry.Action.CONFLICT_RESOLUTION).exists()

    def test_editor_can_resolve_take_sheet(self, api_client, editor, sync_run, make_bid):
        bid = make_bid(remarks="editor typed this")
        bid.locally_overridden = ["remarks"]
        bid.save()
        conflict = self.make_conflict(sync_run, bid)

        login(api_client, editor, "EditorPass123!")
        response = api_client.post(f"/api/v1/sync/conflicts/{conflict.id}/resolve/", {"choose": "sheet"})
        assert response.status_code == 200

        bid.refresh_from_db()
        conflict.refresh_from_db()
        assert bid.remarks == "sheet says this"
        assert "remarks" not in bid.locally_overridden
        assert conflict.resolution == "sheet"

    def test_admin_can_resolve_too(self, api_client, admin_user, sync_run, make_bid):
        bid = make_bid()
        conflict = self.make_conflict(sync_run, bid)
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post(f"/api/v1/sync/conflicts/{conflict.id}/resolve/", {"choose": "local"})
        assert response.status_code == 200
