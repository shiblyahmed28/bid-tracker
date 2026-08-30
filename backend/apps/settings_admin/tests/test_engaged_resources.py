"""§Phase 20 items 2-4: the enhanced Engaged Resources management screen
(filters, full field set), the duplicate-detection/merge tool, and per-person
engagement history."""

import pytest

from apps.audit.models import AuditEntry
from apps.bids.models import Bid, BidEngagement, Client, Person
from apps.settings_admin.services import SamePersonError, find_duplicate_person_groups, merge_persons

from conftest import login


@pytest.fixture
def client_obj(db):
    return Client.objects.create(name="Engaged Resources Co", canonical_name="engaged resources co")


@pytest.fixture
def make_bid(db, client_obj):
    def _make(**kwargs):
        kwargs.setdefault("client", client_obj)
        kwargs.setdefault("description", "x")
        kwargs.setdefault("submission_date", "2026-09-01")
        return Bid.objects.create(**kwargs)

    return _make


@pytest.mark.django_db
class TestSettingsPersonFields:
    def test_create_with_full_field_set(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post(
            "/api/v1/settings/people/",
            {
                "canonical_name": "Jane Doe",
                "email": "jane@example.com",
                "person_type": "external",
                "organization": "Partner Co",
                "phone": "+880-1000",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["person_type"] == "external"
        assert response.data["organization"] == "Partner Co"
        assert response.data["usage_count"] == 0

    def test_duplicate_email_is_rejected(self, api_client, admin_user):
        Person.objects.create(canonical_name="Existing", email="dup@example.com")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post(
            "/api/v1/settings/people/",
            {"canonical_name": "New Person", "email": "dup@example.com"},
            format="json",
        )
        assert response.status_code == 400

    def test_deactivate_via_patch(self, api_client, admin_user):
        person = Person.objects.create(canonical_name="Deactivate Me")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.patch(
            f"/api/v1/settings/people/{person.id}/", {"is_active": False}, format="json"
        )
        assert response.status_code == 200
        person.refresh_from_db()
        assert person.is_active is False

    def test_link_user_account(self, api_client, admin_user, editor):
        person = Person.objects.create(canonical_name="Linked Person")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.patch(
            f"/api/v1/settings/people/{person.id}/", {"user": editor.id}, format="json"
        )
        assert response.status_code == 200
        assert response.data["user_email"] == editor.email

    def test_filter_by_person_type(self, api_client, admin_user):
        Person.objects.create(canonical_name="Internal One", person_type="internal")
        Person.objects.create(canonical_name="External One", person_type="external")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/settings/people/", {"person_type": "external"})
        names = [p["canonical_name"] for p in response.data]
        assert names == ["External One"]

    def test_filter_by_is_active(self, api_client, admin_user):
        Person.objects.create(canonical_name="Active One", is_active=True)
        Person.objects.create(canonical_name="Inactive One", is_active=False)
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/settings/people/", {"is_active": "false"})
        names = [p["canonical_name"] for p in response.data]
        assert names == ["Inactive One"]

    def test_editor_gets_403(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.post(
            "/api/v1/settings/people/", {"canonical_name": "Nope"}, format="json"
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestDuplicateDetection:
    def test_finds_whitespace_and_case_variants(self):
        Person.objects.create(canonical_name="Aminul Quader Khalili")
        # Simulate a historical row that predates today's case-insensitive
        # create/sync guards — bypass the ORM's own validation by using
        # .update() so the DB-level (case-sensitive) unique constraint is
        # the only thing that could stop this, and it doesn't.
        variant = Person.objects.create(canonical_name="AMINUL QUADER KHALILI TEMP")
        Person.objects.filter(pk=variant.pk).update(canonical_name="aminul quader khalili")

        groups = find_duplicate_person_groups()
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_no_false_positives_for_distinct_names(self):
        Person.objects.create(canonical_name="Alpha Person")
        Person.objects.create(canonical_name="Beta Person")
        assert find_duplicate_person_groups() == []

    def test_duplicates_endpoint(self, api_client, admin_user):
        Person.objects.create(canonical_name="Dup One")
        dup2 = Person.objects.create(canonical_name="Dup One Temp")
        Person.objects.filter(pk=dup2.pk).update(canonical_name="dup one")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/settings/people/duplicates/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert len(response.data[0]["people"]) == 2


@pytest.mark.django_db
class TestMergePersons:
    def test_reassigns_engagements_and_deactivates_duplicate(self, make_bid):
        survivor = Person.objects.create(canonical_name="Survivor")
        duplicate = Person.objects.create(canonical_name="Duplicate")
        bid = make_bid()
        BidEngagement.objects.create(bid=bid, person=duplicate, days=5)

        from apps.accounts.models import User

        admin = User.objects.create_user(email="merge-admin@spectrum-bd.com", password="x", role="admin")
        merge_persons(survivor, duplicate, admin)

        duplicate.refresh_from_db()
        assert duplicate.is_active is False
        assert BidEngagement.objects.filter(person=survivor, bid=bid).exists()
        assert not BidEngagement.objects.filter(person=duplicate).exists()

    def test_skips_collision_when_survivor_already_engaged_on_same_bid(self, make_bid):
        survivor = Person.objects.create(canonical_name="Survivor")
        duplicate = Person.objects.create(canonical_name="Duplicate")
        bid = make_bid()
        BidEngagement.objects.create(bid=bid, person=survivor, days=10)
        BidEngagement.objects.create(bid=bid, person=duplicate, days=3)

        from apps.accounts.models import User

        admin = User.objects.create_user(email="merge-admin2@spectrum-bd.com", password="x", role="admin")
        result = merge_persons(survivor, duplicate, admin)

        assert result["engagements_skipped"] == 1
        assert result["engagements_reassigned"] == 0
        survivor_engagement = BidEngagement.objects.get(person=survivor, bid=bid)
        assert survivor_engagement.days == 10  # survivor's own row wins, untouched

    def test_reassigns_cam_sales_resource_bid_manager(self, make_bid):
        survivor = Person.objects.create(canonical_name="Survivor")
        duplicate = Person.objects.create(canonical_name="Duplicate")
        bid = make_bid(cam=duplicate, sales_resource=duplicate, bid_manager=duplicate)

        from apps.accounts.models import User

        admin = User.objects.create_user(email="merge-admin3@spectrum-bd.com", password="x", role="admin")
        merge_persons(survivor, duplicate, admin)

        bid.refresh_from_db()
        assert bid.cam_id == survivor.id
        assert bid.sales_resource_id == survivor.id
        assert bid.bid_manager_id == survivor.id

    def test_writes_one_audit_entry(self, make_bid):
        survivor = Person.objects.create(canonical_name="Survivor")
        duplicate = Person.objects.create(canonical_name="Duplicate")

        from apps.accounts.models import User

        admin = User.objects.create_user(email="merge-admin4@spectrum-bd.com", password="x", role="admin")
        before = AuditEntry.objects.count()
        merge_persons(survivor, duplicate, admin)
        assert AuditEntry.objects.count() == before + 1
        entry = AuditEntry.objects.filter(action=AuditEntry.Action.PERSON_MERGE).latest("created_at")
        assert entry.old_value == "Duplicate"
        assert "Survivor" in entry.new_value

    def test_cannot_merge_person_into_themselves(self):
        person = Person.objects.create(canonical_name="Solo")
        from apps.accounts.models import User

        admin = User.objects.create_user(email="merge-admin5@spectrum-bd.com", password="x", role="admin")
        with pytest.raises(SamePersonError):
            merge_persons(person, person, admin)

    def test_merge_via_api(self, api_client, admin_user, make_bid):
        survivor = Person.objects.create(canonical_name="API Survivor")
        duplicate = Person.objects.create(canonical_name="API Duplicate")
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post(
            f"/api/v1/settings/people/{survivor.id}/merge/", {"duplicate_id": duplicate.id}, format="json"
        )
        assert response.status_code == 200
        duplicate.refresh_from_db()
        assert duplicate.is_active is False


@pytest.mark.django_db
class TestPersonEngagementHistory:
    def test_returns_engagements_with_bid_info_and_totals(self, api_client, admin_user, make_bid):
        from decimal import Decimal

        person = Person.objects.create(canonical_name="History Person")
        bid1 = make_bid(description="first")
        bid2 = make_bid(description="second")
        BidEngagement.objects.create(bid=bid1, person=person, days=4, convenience_bill=Decimal("1000"))
        BidEngagement.objects.create(bid=bid2, person=person, days=6, convenience_bill=Decimal("2000"))

        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get(f"/api/v1/settings/people/{person.id}/engagements/")
        assert response.status_code == 200
        assert len(response.data["engagements"]) == 2
        assert response.data["totals"]["days"] == 10
        assert response.data["totals"]["convenience_bill"] == Decimal("3000.00")
        assert {e["bid"]["reference"] for e in response.data["engagements"]} == {bid1.reference, bid2.reference}

    def test_editor_gets_403(self, api_client, editor):
        person = Person.objects.create(canonical_name="Blocked Person")
        login(api_client, editor, "EditorPass123!")
        response = api_client.get(f"/api/v1/settings/people/{person.id}/engagements/")
        assert response.status_code == 403
