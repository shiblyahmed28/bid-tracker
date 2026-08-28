import pytest

from apps.accounts.models import User
from apps.audit.models import AuditEntry
from apps.bids.models import Bid, Client
from apps.settings_admin.models import UserCapability
from apps.settings_admin.services import (
    LastAdminError,
    SelfLockoutError,
    clear_capability_override,
    grant_capability,
    guard_last_admin_demotion,
)

from conftest import login


@pytest.fixture
def bid(db):
    client_obj = Client.objects.create(name="Cap Test Co", canonical_name="cap test co")
    return Bid.objects.create(client=client_obj, description="test", submission_date="2026-09-10")


@pytest.mark.django_db
def test_role_defaults_match_previous_role_gates(viewer, editor, admin_user):
    assert viewer.has_capability("export_pdf") is True
    assert viewer.has_capability("create_bid") is False
    assert viewer.has_capability("delete_bid") is False

    assert editor.has_capability("create_bid") is True
    assert editor.has_capability("edit_bid") is True
    assert editor.has_capability("delete_bid") is False
    assert editor.has_capability("manage_users") is False

    assert admin_user.has_capability("delete_bid") is True
    assert admin_user.has_capability("manage_users") is True
    assert admin_user.has_capability("access_master_settings") is True


@pytest.mark.django_db
def test_explicit_override_wins_over_role_default(viewer, admin_user):
    grant_capability(viewer, "access_master_settings", True, admin_user)
    assert viewer.has_capability("access_master_settings") is True


@pytest.mark.django_db
def test_grant_and_revoke_capability_writes_audit_entry_naming_both_users(viewer, admin_user):
    grant_capability(viewer, "access_master_settings", True, admin_user)
    entry = AuditEntry.objects.filter(action=AuditEntry.Action.CAPABILITY_GRANT).latest("created_at")
    assert entry.actor == admin_user
    assert viewer.email in entry.new_value
    assert admin_user.email in entry.new_value


@pytest.mark.django_db
def test_admin_cannot_revoke_manage_users_from_self(admin_user):
    with pytest.raises(SelfLockoutError):
        grant_capability(admin_user, "manage_users", False, admin_user)


@pytest.mark.django_db
def test_admin_cannot_revoke_access_master_settings_from_self(admin_user):
    with pytest.raises(SelfLockoutError):
        grant_capability(admin_user, "access_master_settings", False, admin_user)


@pytest.mark.django_db
def test_admin_can_revoke_unprotected_capability_from_self(admin_user):
    # e.g. an admin removing their own delete_bid isn't a lockout risk.
    grant_capability(admin_user, "delete_bid", False, admin_user)
    assert admin_user.has_capability("delete_bid") is False


@pytest.mark.django_db
def test_clear_override_reverts_to_role_default(viewer, admin_user):
    grant_capability(viewer, "export_pdf", False, admin_user)
    assert viewer.has_capability("export_pdf") is False

    clear_capability_override(viewer, "export_pdf", admin_user)
    assert viewer.has_capability("export_pdf") is True  # back to viewer's role default


@pytest.mark.django_db
def test_clear_own_override_is_safe_when_role_default_still_grants_it(admin_user):
    # admin's role default already includes manage_users, so an admin
    # clearing their own override for it lands back on True — not a lockout.
    grant_capability(admin_user, "manage_users", True, admin_user)
    clear_capability_override(admin_user, "manage_users", admin_user)  # must not raise
    assert admin_user.has_capability("manage_users") is True


@pytest.mark.django_db
def test_clear_override_blocked_for_non_admin_role_with_protected_capability(editor, admin_user):
    grant_capability(editor, "access_master_settings", True, admin_user)
    with pytest.raises(SelfLockoutError):
        clear_capability_override(editor, "access_master_settings", editor)


@pytest.mark.django_db
def test_clear_override_via_api(api_client, viewer, admin_user):
    grant_capability(viewer, "export_pdf", False, admin_user)
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.delete(f"/api/v1/settings/users/{viewer.id}/capabilities/?capability=export_pdf")
    assert response.status_code == 200
    viewer.refresh_from_db()
    assert viewer.has_capability("export_pdf") is True


@pytest.mark.django_db
def test_last_remaining_admin_cannot_be_demoted(admin_user):
    with pytest.raises(LastAdminError):
        guard_last_admin_demotion(admin_user, User.Role.EDITOR)


@pytest.mark.django_db
def test_admin_can_be_demoted_when_another_admin_remains(admin_user):
    User.objects.create_user(email="second-admin@spectrum-bd.com", password="Pass1234567!", role=User.Role.ADMIN)
    guard_last_admin_demotion(admin_user, User.Role.EDITOR)  # must not raise


@pytest.mark.django_db
def test_viewer_granted_access_master_settings_can_reach_settings_api_but_not_delete_bid(
    api_client, viewer, admin_user, bid
):
    """The literal Phase 15 acceptance criterion."""
    grant_capability(viewer, "access_master_settings", True, admin_user)

    login(api_client, viewer, "ViewerPass123!")

    settings_response = api_client.get("/api/v1/settings/choice-lists/")
    assert settings_response.status_code == 200

    delete_response = api_client.delete(f"/api/v1/bids/{bid.id}/")
    assert delete_response.status_code == 403


@pytest.mark.django_db
def test_viewer_without_capability_gets_403_on_settings_api(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.get("/api/v1/settings/choice-lists/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_editor_with_delete_bid_override_can_delete(api_client, editor, admin_user, bid):
    grant_capability(editor, "delete_bid", True, admin_user)
    login(api_client, editor, "EditorPass123!")
    response = api_client.delete(f"/api/v1/bids/{bid.id}/")
    assert response.status_code == 204


@pytest.mark.django_db
def test_user_capabilities_endpoint_shows_effective_state(api_client, viewer, admin_user):
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.get(f"/api/v1/settings/users/{viewer.id}/capabilities/")
    assert response.status_code == 200
    by_cap = {row["capability"]: row for row in response.data["effective"]}
    assert by_cap["export_pdf"]["granted"] is True
    assert by_cap["export_pdf"]["source"] == "role_default"
    assert by_cap["delete_bid"]["granted"] is False


@pytest.mark.django_db
def test_user_capabilities_endpoint_self_lockout_returns_400(api_client, admin_user):
    login(api_client, admin_user, "AdminPass123!")
    response = api_client.post(
        f"/api/v1/settings/users/{admin_user.id}/capabilities/",
        {"capability": "manage_users", "granted": False},
        format="json",
    )
    assert response.status_code == 400
