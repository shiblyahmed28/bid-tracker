import pytest

from apps.audit.models import AuditEntry
from apps.bids.models import Client, Person, Team

from conftest import login


@pytest.mark.django_db
class TestClientCreate:
    def test_admin_can_create_and_canonical_name_is_derived(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/settings/clients/", {"name": "  Acme   Corp "}, format="json")
        assert response.status_code == 201
        client = Client.objects.get(pk=response.data["id"])
        # DRF's CharField trims outer whitespace by default; canonical_name
        # additionally collapses internal runs via norm_text (§8).
        assert client.name == "Acme   Corp"
        assert client.canonical_name == "Acme Corp"

    def test_create_writes_an_audit_entry(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        before = AuditEntry.objects.count()
        api_client.post("/api/v1/settings/clients/", {"name": "New Client Co"}, format="json")
        assert AuditEntry.objects.count() == before + 1

    def test_duplicate_name_is_rejected_not_a_500(self, api_client, admin_user):
        Client.objects.create(name="Existing Co", canonical_name="Existing Co")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/settings/clients/", {"name": "existing co"}, format="json")
        assert response.status_code == 400

    def test_editor_gets_403(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.post("/api/v1/settings/clients/", {"name": "Nope Co"}, format="json")
        assert response.status_code == 403

    def test_rename_keeps_canonical_name_in_sync(self, api_client, admin_user):
        client = Client.objects.create(name="Old Name", canonical_name="Old Name")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.patch(f"/api/v1/settings/clients/{client.id}/", {"name": "New Name"}, format="json")
        assert response.status_code == 200
        client.refresh_from_db()
        assert client.canonical_name == "New Name"


@pytest.mark.django_db
class TestPersonCreate:
    def test_admin_can_create(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/settings/people/", {"canonical_name": "  Jane   Doe "}, format="json")
        assert response.status_code == 201
        assert Person.objects.get(pk=response.data["id"]).canonical_name == "Jane Doe"

    def test_case_insensitive_duplicate_is_rejected(self, api_client, admin_user):
        Person.objects.create(canonical_name="John Doe")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/settings/people/", {"canonical_name": "john doe"}, format="json")
        assert response.status_code == 400


@pytest.mark.django_db
class TestTeamCreate:
    def test_admin_can_create(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/settings/teams/", {"name": "Special Projects"}, format="json")
        assert response.status_code == 201
        team = Team.objects.get(pk=response.data["id"])
        assert team.is_active is True

    def test_duplicate_name_is_rejected(self, api_client, admin_user):
        Team.objects.get(name="Government")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/settings/teams/", {"name": "government"}, format="json")
        assert response.status_code == 400

    def test_deactivate_via_patch(self, api_client, admin_user):
        team = Team.objects.create(name="Deactivate Me")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.patch(f"/api/v1/settings/teams/{team.id}/", {"is_active": False}, format="json")
        assert response.status_code == 200
        team.refresh_from_db()
        assert team.is_active is False
