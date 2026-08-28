import pytest

from apps.accounts.models import UserSession
from apps.audit.models import AuditEntry

from .conftest import DESKTOP_UA, MOBILE_UA, login


@pytest.mark.django_db
def test_login_creates_session_with_parsed_device_info(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!", user_agent=DESKTOP_UA)
    session = UserSession.objects.get(user=viewer)
    assert session.device_type == UserSession.DeviceType.DESKTOP
    assert "Chrome" in session.browser
    assert "Windows" in session.os


@pytest.mark.django_db
def test_two_logins_from_different_user_agents_create_two_sessions_with_different_device_types(
    api_client, viewer
):
    login(api_client, viewer, "ViewerPass123!", user_agent=DESKTOP_UA)
    api_client.credentials()
    login(api_client, viewer, "ViewerPass123!", user_agent=MOBILE_UA)

    sessions = UserSession.objects.filter(user=viewer).order_by("created_at")
    assert sessions.count() == 2
    assert sessions[0].device_type == UserSession.DeviceType.DESKTOP
    assert sessions[1].device_type == UserSession.DeviceType.MOBILE
    assert sessions[1].device_brand == "Apple"


@pytest.mark.django_db
def test_sessions_endpoint_lists_own_sessions_newest_first_and_flags_current(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!", user_agent=DESKTOP_UA)
    api_client.credentials()
    response = login(api_client, viewer, "ViewerPass123!", user_agent=MOBILE_UA)
    current_access = response.data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {current_access}")

    listing = api_client.get("/api/v1/auth/sessions/")
    assert listing.status_code == 200
    rows = listing.data["results"] if isinstance(listing.data, dict) else listing.data
    assert len(rows) == 2
    # newest first
    assert rows[0]["device_type"] == UserSession.DeviceType.MOBILE
    assert rows[0]["is_current"] is True
    assert rows[1]["is_current"] is False


@pytest.mark.django_db
def test_refresh_bumps_last_seen_and_keeps_current_flag_accurate(api_client, viewer):
    login_response = login(api_client, viewer, "ViewerPass123!")
    refresh_token = login_response.data["refresh"]
    session = UserSession.objects.get(user=viewer)
    original_jti = session.refresh_jti
    original_last_seen = session.last_seen_at

    api_client.credentials()
    refresh_response = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh_token})
    assert refresh_response.status_code == 200

    session.refresh_from_db()
    assert session.refresh_jti != original_jti
    assert session.last_seen_at >= original_last_seen

    new_access = refresh_response.data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
    listing = api_client.get("/api/v1/auth/sessions/")
    rows = listing.data["results"] if isinstance(listing.data, dict) else listing.data
    assert rows[0]["is_current"] is True


@pytest.mark.django_db
def test_revoke_others_leaves_exactly_one_active(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!", user_agent=DESKTOP_UA)
    api_client.credentials()
    login(api_client, viewer, "ViewerPass123!", user_agent=MOBILE_UA)
    api_client.credentials()
    current = login(api_client, viewer, "ViewerPass123!", user_agent=DESKTOP_UA)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {current.data['access']}")

    assert UserSession.objects.filter(user=viewer, revoked_at__isnull=True).count() == 3

    response = api_client.post("/api/v1/auth/sessions/revoke-others/")
    assert response.status_code == 200
    assert response.data["revoked"] == 2

    active = [s for s in UserSession.objects.filter(user=viewer) if s.is_active]
    assert len(active) == 1
    assert AuditEntry.objects.filter(action=AuditEntry.Action.SESSION_REVOKE).count() == 2


@pytest.mark.django_db
def test_viewer_cannot_view_another_users_sessions(api_client, viewer, editor):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.get(f"/api/v1/users/{editor.id}/sessions/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_view_any_users_sessions(api_client, admin_user, viewer):
    login(api_client, viewer, "ViewerPass123!")
    api_client.credentials()
    login(api_client, admin_user, "AdminPass123!")

    response = api_client.get(f"/api/v1/users/{viewer.id}/sessions/")
    assert response.status_code == 200
    rows = response.data["results"] if isinstance(response.data, dict) else response.data
    assert len(rows) == 1


@pytest.mark.django_db
def test_user_can_revoke_own_session(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    session = UserSession.objects.get(user=viewer)

    response = api_client.post(f"/api/v1/auth/sessions/{session.id}/revoke/")
    assert response.status_code == 204
    session.refresh_from_db()
    assert session.revoked_at is not None
    assert AuditEntry.objects.filter(action=AuditEntry.Action.SESSION_REVOKE).exists()


@pytest.mark.django_db
def test_viewer_cannot_revoke_someone_elses_session(api_client, viewer, editor):
    login(api_client, editor, "EditorPass123!")
    editor_session = UserSession.objects.get(user=editor)
    api_client.credentials()

    login(api_client, viewer, "ViewerPass123!")
    response = api_client.post(f"/api/v1/auth/sessions/{editor_session.id}/revoke/")
    assert response.status_code == 403
    editor_session.refresh_from_db()
    assert editor_session.revoked_at is None


@pytest.mark.django_db
def test_admin_can_revoke_someone_elses_session(api_client, admin_user, viewer):
    login(api_client, viewer, "ViewerPass123!")
    viewer_session = UserSession.objects.get(user=viewer)
    api_client.credentials()

    login(api_client, admin_user, "AdminPass123!")
    response = api_client.post(f"/api/v1/auth/sessions/{viewer_session.id}/revoke/")
    assert response.status_code == 204
    viewer_session.refresh_from_db()
    assert viewer_session.revoked_at is not None


@pytest.mark.django_db
def test_logout_marks_session_revoked(api_client, viewer):
    login_response = login(api_client, viewer, "ViewerPass123!")
    session = UserSession.objects.get(user=viewer)

    api_client.post("/api/v1/auth/logout/", {"refresh": login_response.data["refresh"]})
    session.refresh_from_db()
    assert session.revoked_at is not None
