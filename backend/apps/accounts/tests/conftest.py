import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def viewer(db):
    return User.objects.create_user(
        email="viewer@spectrum-bd.com", password="ViewerPass123!", role=User.Role.VIEWER
    )


@pytest.fixture
def editor(db):
    return User.objects.create_user(
        email="editor@spectrum-bd.com", password="EditorPass123!", role=User.Role.EDITOR
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@spectrum-bd.com",
        password="AdminPass123!",
        role=User.Role.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


def login(api_client, user, password, user_agent=DESKTOP_UA):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": password},
        HTTP_USER_AGENT=user_agent,
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response
