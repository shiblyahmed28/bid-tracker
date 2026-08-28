import pytest

from apps.audit.models import AuditEntry

from .conftest import login


@pytest.mark.django_db
def test_successful_login_returns_tokens_and_writes_audit(api_client, viewer):
    response = api_client.post(
        "/api/v1/auth/login/", {"email": viewer.email, "password": "ViewerPass123!"}
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data
    assert AuditEntry.objects.filter(action=AuditEntry.Action.SIGN_IN, actor=viewer).exists()


@pytest.mark.django_db
def test_failed_login_returns_401_and_writes_audit(api_client, viewer):
    response = api_client.post(
        "/api/v1/auth/login/", {"email": viewer.email, "password": "wrong-password"}
    )
    assert response.status_code == 401
    entry = AuditEntry.objects.filter(action=AuditEntry.Action.SIGN_IN_FAILED).first()
    assert entry is not None
    assert entry.actor_label == viewer.email
    assert entry.actor is None


@pytest.mark.django_db
def test_unauthenticated_request_returns_401(api_client):
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_endpoint_returns_current_user(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == 200
    assert response.data["email"] == viewer.email
    assert response.data["role"] == viewer.role


@pytest.mark.django_db
def test_logout_blacklists_refresh_token_and_writes_audit(api_client, viewer):
    login_response = api_client.post(
        "/api/v1/auth/login/", {"email": viewer.email, "password": "ViewerPass123!"}
    )
    access, refresh = login_response.data["access"], login_response.data["refresh"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.post("/api/v1/auth/logout/", {"refresh": refresh})
    assert response.status_code == 205
    assert AuditEntry.objects.filter(action=AuditEntry.Action.SIGN_OUT, actor=viewer).exists()

    api_client.credentials()
    refresh_response = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh})
    assert refresh_response.status_code == 401
