"""§Phase 21 item 1 — external-domain accounts via the /users/ API: any
domain allowed, forced to viewer, can't be promoted, badged, and audited
with a distinct action naming the creating admin."""

import pytest

from apps.audit.models import AuditEntry
from apps.notifications.models import SentEmail

from conftest import login


@pytest.mark.django_db
class TestExternalAccountCreation:
    def test_admin_can_create_external_viewer(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post(
            "/api/v1/users/",
            {"email": "partner@example.com", "full_name": "Partner", "password": "Password123!", "role": "viewer"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["is_external"] is True
        assert response.data["role"] == "viewer"

    def test_admin_cannot_create_external_editor(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post(
            "/api/v1/users/",
            {"email": "partner2@example.com", "full_name": "Partner", "password": "Password123!", "role": "editor"},
            format="json",
        )
        assert response.status_code == 400
        assert "role" in response.data

    def test_external_creation_is_audited_with_a_distinct_action_and_the_admins_name(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        api_client.post(
            "/api/v1/users/",
            {"email": "partner3@example.com", "full_name": "Partner", "password": "Password123!", "role": "viewer"},
            format="json",
        )
        entry = AuditEntry.objects.filter(action=AuditEntry.Action.EXTERNAL_USER_CREATE).latest("created_at")
        assert entry.actor == admin_user
        assert entry.actor_label == admin_user.email
        assert "partner3@example.com" in entry.new_value

    def test_company_domain_creation_uses_the_plain_user_create_action(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        api_client.post(
            "/api/v1/users/",
            {
                "email": "colleague@spectrum-bd.com",
                "full_name": "Colleague",
                "password": "Password123!",
                "role": "editor",
            },
            format="json",
        )
        entry = AuditEntry.objects.filter(new_value__icontains="colleague@spectrum-bd.com").latest("created_at")
        assert entry.action == AuditEntry.Action.USER_CREATE

    def test_cannot_promote_an_existing_external_account_via_api(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        create = api_client.post(
            "/api/v1/users/",
            {"email": "partner4@example.com", "full_name": "Partner", "password": "Password123!", "role": "viewer"},
            format="json",
        )
        user_id = create.data["id"]
        response = api_client.patch(f"/api/v1/users/{user_id}/", {"role": "editor"}, format="json")
        assert response.status_code == 400

    def test_editor_gets_403(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.post(
            "/api/v1/users/",
            {"email": "partner5@example.com", "full_name": "Partner", "password": "Password123!", "role": "viewer"},
            format="json",
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestPasswordResetEmailLogging:
    """The admin-password-reset email bypasses apps.notifications.emails._send()
    entirely (plain send_mail, no template) — confirms it still gets logged."""

    def test_password_reset_email_is_logged(self, api_client, admin_user, viewer):
        login(api_client, admin_user, "AdminPass123!")
        SentEmail.objects.all().delete()
        response = api_client.post(
            f"/api/v1/users/{viewer.id}/reset-password/",
            {
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
                "force_change": True,
                "email_user": True,
                "revoke_sessions": False,
            },
            format="json",
        )
        assert response.status_code == 200
        entry = SentEmail.objects.get()
        assert entry.to_email == viewer.email
        assert entry.kind == SentEmail.Kind.PASSWORD_RESET
        assert entry.success is True
