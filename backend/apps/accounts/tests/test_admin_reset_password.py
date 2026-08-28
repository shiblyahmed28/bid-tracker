import pytest
from django.core import mail

from apps.accounts.models import UserSession
from apps.audit.models import AuditEntry

from .conftest import login


@pytest.mark.django_db
def test_admin_reset_password_sets_new_password_and_audits(api_client, admin_user, viewer):
    login(api_client, admin_user, "AdminPass123!")

    response = api_client.post(
        f"/api/v1/users/{viewer.id}/reset-password/",
        {
            "new_password": "AdminChosenPass1!",
            "confirm_password": "AdminChosenPass1!",
            "force_change": True,
            "email_user": True,
            "revoke_sessions": True,
        },
    )
    assert response.status_code == 200

    viewer.refresh_from_db()
    assert viewer.check_password("AdminChosenPass1!")
    assert viewer.must_change_password is True

    entry = AuditEntry.objects.get(action=AuditEntry.Action.PASSWORD_RESET)
    assert entry.actor == admin_user
    assert viewer.email in entry.new_value
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [viewer.email]
    # never the raw password
    assert "AdminChosenPass1!" not in mail.outbox[0].body


@pytest.mark.django_db
def test_admin_reset_password_revokes_target_sessions(api_client, admin_user, viewer):
    login(api_client, viewer, "ViewerPass123!")
    api_client.credentials()

    login(api_client, admin_user, "AdminPass123!")
    api_client.post(
        f"/api/v1/users/{viewer.id}/reset-password/",
        {
            "new_password": "AdminChosenPass1!",
            "confirm_password": "AdminChosenPass1!",
            "revoke_sessions": True,
            "force_change": False,
            "email_user": False,
        },
    )

    active = [s for s in UserSession.objects.filter(user=viewer) if s.is_active]
    assert active == []
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_admin_reset_password_short_password_rejected(api_client, admin_user, viewer):
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.post(
        f"/api/v1/users/{viewer.id}/reset-password/",
        {"new_password": "short1!", "confirm_password": "short1!"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_non_admin_cannot_reset_password(api_client, editor, viewer):
    login(api_client, editor, "EditorPass123!")
    response = api_client.post(
        f"/api/v1/users/{viewer.id}/reset-password/",
        {"new_password": "AdminChosenPass1!", "confirm_password": "AdminChosenPass1!"},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_never_sees_existing_password_hash(api_client, admin_user, viewer):
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.get(f"/api/v1/users/{viewer.id}/")
    assert "password" not in response.data
