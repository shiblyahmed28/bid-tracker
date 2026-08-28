import pytest

from apps.accounts.models import User
from apps.audit.models import AuditEntry

from .conftest import login


@pytest.mark.django_db
def test_profile_update_saves_and_writes_audit_entries(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")

    response = api_client.patch(
        "/api/v1/auth/profile/",
        {"full_name": "Viewer Renamed", "phone": "+8801712345678"},
    )
    assert response.status_code == 200
    viewer.refresh_from_db()
    assert viewer.full_name == "Viewer Renamed"
    assert viewer.phone == "+8801712345678"

    entries = AuditEntry.objects.filter(actor=viewer, action=AuditEntry.Action.USER_UPDATE)
    assert entries.filter(field="full_name").exists()
    assert entries.filter(field="phone").exists()


@pytest.mark.django_db
def test_profile_update_rejects_non_company_email(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.patch("/api/v1/auth/profile/", {"email": "viewer@gmail.com"})
    assert response.status_code == 400
    assert "email" in response.data
    viewer.refresh_from_db()
    assert viewer.email == "viewer@spectrum-bd.com"


@pytest.mark.django_db
def test_profile_update_role_and_join_date_are_read_only(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.patch("/api/v1/auth/profile/", {"role": User.Role.ADMIN})
    assert response.status_code == 200
    viewer.refresh_from_db()
    assert viewer.role == User.Role.VIEWER


@pytest.mark.django_db
def test_profile_update_only_affects_own_account(api_client, viewer, editor):
    login(api_client, viewer, "ViewerPass123!")
    api_client.patch("/api/v1/auth/profile/", {"full_name": "Should only touch viewer"})
    editor.refresh_from_db()
    assert editor.full_name == ""
