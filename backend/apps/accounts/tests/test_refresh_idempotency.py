import time

import pytest
from django.core.cache import cache

import apps.accounts.serializers as serializers_module
from apps.accounts.models import UserSession

from .conftest import login


@pytest.fixture(autouse=True)
def _clear_idempotency_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_same_refresh_token_presented_twice_within_the_window_returns_the_same_pair(api_client, viewer):
    """ROTATE_REFRESH_TOKENS blacklists the old token on the first rotation —
    a second in-flight request presenting that identical token would
    otherwise 401 with "token is blacklisted" even though it asked for the
    same thing a moment earlier."""
    login_response = login(api_client, viewer, "ViewerPass123!")
    refresh_token = login_response.data["refresh"]
    api_client.credentials()

    first = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh_token})
    assert first.status_code == 200

    second = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh_token})
    assert second.status_code == 200
    assert second.data["access"] == first.data["access"]
    assert second.data["refresh"] == first.data["refresh"]


@pytest.mark.django_db
def test_same_refresh_token_presented_after_the_window_is_rejected(api_client, viewer, monkeypatch):
    """Outside the idempotency window a blacklisted token is rejected as
    normal — genuine token reuse is still a real signal."""
    monkeypatch.setattr(serializers_module, "REFRESH_IDEMPOTENCY_TTL_SECONDS", 1)

    login_response = login(api_client, viewer, "ViewerPass123!")
    refresh_token = login_response.data["refresh"]
    api_client.credentials()

    first = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh_token})
    assert first.status_code == 200

    time.sleep(1.2)

    second = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh_token})
    assert second.status_code == 401


@pytest.mark.django_db
def test_an_unrelated_garbage_token_is_still_rejected(api_client, viewer):
    """The idempotency cache only ever short-circuits the *identical* token
    it cached a response for — nothing else gets waved through."""
    login(api_client, viewer, "ViewerPass123!")
    api_client.credentials()

    response = api_client.post("/api/v1/auth/refresh/", {"refresh": "not-a-real-token"})
    assert response.status_code == 401


@pytest.mark.django_db
def test_cached_refresh_response_does_not_reassign_the_session_a_second_time(api_client, viewer):
    login_response = login(api_client, viewer, "ViewerPass123!")
    refresh_token = login_response.data["refresh"]
    session = UserSession.objects.get(user=viewer)
    api_client.credentials()

    api_client.post("/api/v1/auth/refresh/", {"refresh": refresh_token})
    session.refresh_from_db()
    jti_after_first = session.refresh_jti

    second = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh_token})
    assert second.status_code == 200
    session.refresh_from_db()
    assert session.refresh_jti == jti_after_first
