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


def login(api_client, user, password):
    response = api_client.post("/api/v1/auth/login/", {"email": user.email, "password": password})
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response
