import pytest

from apps.accounts.models import UserSession
from apps.audit.models import AuditEntry

from .conftest import DESKTOP_UA, MOBILE_UA, login


@pytest.mark.django_db
def test_change_password_succeeds_and_new_password_works(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.post(
        "/api/v1/auth/change-password/",
        {
            "current_password": "ViewerPass123!",
            "new_password": "BrandNewPass456!",
            "confirm_password": "BrandNewPass456!",
        },
    )
    assert response.status_code == 200

    api_client.credentials()
    relogin = login(api_client, viewer, "BrandNewPass456!")
    assert relogin.status_code == 200
    assert AuditEntry.objects.filter(actor=viewer, action=AuditEntry.Action.PASSWORD_CHANGE).exists()


@pytest.mark.django_db
def test_change_password_wrong_current_password_rejected(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.post(
        "/api/v1/auth/change-password/",
        {
            "current_password": "WrongPassword!",
            "new_password": "BrandNewPass456!",
            "confirm_password": "BrandNewPass456!",
        },
    )
    assert response.status_code == 400
    assert "current_password" in response.data


@pytest.mark.django_db
def test_change_password_too_short_rejected(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.post(
        "/api/v1/auth/change-password/",
        {
            "current_password": "ViewerPass123!",
            "new_password": "short1!",
            "confirm_password": "short1!",
        },
    )
    assert response.status_code == 400
    assert "new_password" in response.data


@pytest.mark.django_db
def test_change_password_mismatched_confirm_rejected(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.post(
        "/api/v1/auth/change-password/",
        {
            "current_password": "ViewerPass123!",
            "new_password": "BrandNewPass456!",
            "confirm_password": "SomethingElse789!",
        },
    )
    assert response.status_code == 400
    assert "confirm_password" in response.data


@pytest.mark.django_db
def test_change_password_kills_other_sessions_but_not_current(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!", user_agent=DESKTOP_UA)
    api_client.credentials()
    current = login(api_client, viewer, "ViewerPass123!", user_agent=MOBILE_UA)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {current.data['access']}")

    assert UserSession.objects.filter(user=viewer, revoked_at__isnull=True).count() == 2

    response = api_client.post(
        "/api/v1/auth/change-password/",
        {
            "current_password": "ViewerPass123!",
            "new_password": "BrandNewPass456!",
            "confirm_password": "BrandNewPass456!",
        },
    )
    assert response.status_code == 200
    assert response.data["revoked_sessions"] == 1

    active = [s for s in UserSession.objects.filter(user=viewer) if s.is_active]
    assert len(active) == 1

    # the still-active session must still be the current device — a follow-up
    # authenticated call on the same access token keeps working.
    me = api_client.get("/api/v1/auth/me/")
    assert me.status_code == 200
