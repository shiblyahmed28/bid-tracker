import pytest

from apps.audit.models import AuditEntry

from conftest import login


@pytest.fixture
def audit_entry(db, admin_user):
    return AuditEntry.objects.create(
        actor=admin_user, actor_label=admin_user.email, action=AuditEntry.Action.SIGN_IN
    )


@pytest.mark.django_db
class TestAuditListRoleMatrix:
    """Explicitly required by Phase 6: viewer AND editor both get 403 on /audit/."""

    def test_viewer_gets_403(self, api_client, viewer, audit_entry):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/audit/")
        assert response.status_code == 403

    def test_editor_gets_403(self, api_client, editor, audit_entry):
        login(api_client, editor, "EditorPass123!")
        response = api_client.get("/api/v1/audit/")
        assert response.status_code == 403

    def test_admin_can_list(self, api_client, admin_user, audit_entry):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/audit/")
        assert response.status_code == 200
        assert response.data["count"] >= 1

    def test_anonymous_gets_401(self, api_client, audit_entry):
        response = api_client.get("/api/v1/audit/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestAuditFilters:
    def test_filter_by_action(self, api_client, admin_user):
        AuditEntry.objects.create(actor=admin_user, action=AuditEntry.Action.SIGN_IN)
        AuditEntry.objects.create(actor=admin_user, action=AuditEntry.Action.SIGN_OUT)
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/audit/", {"action": "sign_in"})
        assert all(row["action"] == "sign_in" for row in response.data["results"])

    def test_filter_by_actor(self, api_client, admin_user, viewer):
        AuditEntry.objects.create(actor=admin_user, action=AuditEntry.Action.SIGN_IN)
        AuditEntry.objects.create(actor=viewer, action=AuditEntry.Action.SIGN_IN)
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/audit/", {"actor": viewer.id})
        assert response.data["count"] == 1
        assert response.data["results"][0]["actor"] == viewer.id


@pytest.mark.django_db
class TestAuditExportRoleMatrix:
    def test_viewer_gets_403(self, api_client, viewer, audit_entry):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/audit/export/")
        assert response.status_code == 403

    def test_editor_gets_403(self, api_client, editor, audit_entry):
        login(api_client, editor, "EditorPass123!")
        response = api_client.get("/api/v1/audit/export/")
        assert response.status_code == 403

    def test_admin_gets_csv(self, api_client, admin_user, audit_entry):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/audit/export/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        body = response.content.decode()
        assert "actor_email" in body.splitlines()[0]
        assert admin_user.email in body
