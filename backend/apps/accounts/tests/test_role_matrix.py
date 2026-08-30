import pytest

from apps.accounts.models import User
from apps.audit.models import AuditEntry

from .conftest import login


@pytest.mark.django_db
def test_viewer_gets_403_on_admin_only_users_endpoint(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.get("/api/v1/users/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_editor_gets_403_on_admin_only_users_endpoint(api_client, editor):
    login(api_client, editor, "EditorPass123!")
    response = api_client.get("/api/v1/users/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_list_users(api_client, admin_user):
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.get("/api/v1/users/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_can_create_user_and_it_is_audited(api_client, admin_user):
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.post(
        "/api/v1/users/",
        {"email": "newperson@spectrum-bd.com", "password": "NewPersonPass123!", "role": User.Role.EDITOR},
        format="json",
    )
    assert response.status_code == 201
    assert User.objects.filter(email="newperson@spectrum-bd.com", role=User.Role.EDITOR).exists()
    assert AuditEntry.objects.filter(action=AuditEntry.Action.USER_CREATE).exists()


@pytest.mark.django_db
def test_admin_can_create_viewer_with_non_company_email(api_client, admin_user):
    """§Phase 21 item 1 — admins may create accounts on any domain now;
    external-domain accounts are just forced to viewer (see
    apps/accounts/tests/test_external_accounts_api.py for the full matrix)."""
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.post(
        "/api/v1/users/",
        {"email": "outsider@gmail.com", "password": "OutsiderPass123!", "role": User.Role.VIEWER},
        format="json",
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_admin_cannot_change_own_role(api_client, admin_user):
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.patch(
        f"/api/v1/users/{admin_user.id}/", {"role": User.Role.VIEWER}, format="json"
    )
    assert response.status_code == 400
    admin_user.refresh_from_db()
    assert admin_user.role == User.Role.ADMIN


@pytest.mark.django_db
def test_admin_can_change_another_users_role_and_it_is_audited(api_client, admin_user, viewer):
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.patch(
        f"/api/v1/users/{viewer.id}/", {"role": User.Role.EDITOR}, format="json"
    )
    assert response.status_code == 200
    viewer.refresh_from_db()
    assert viewer.role == User.Role.EDITOR
    assert AuditEntry.objects.filter(
        action=AuditEntry.Action.ROLE_CHANGE, field="role", old_value="viewer", new_value="editor"
    ).exists()
