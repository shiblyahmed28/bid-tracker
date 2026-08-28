import datetime

import pytest

from apps.audit.models import AuditEntry
from apps.bids.models import Bid, Person

from conftest import login


@pytest.mark.django_db
class TestBidListRoleMatrix:
    def test_viewer_can_list(self, api_client, viewer, make_bid):
        make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/")
        assert response.status_code == 200

    def test_editor_can_list(self, api_client, editor, make_bid):
        make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, editor, "EditorPass123!")
        response = api_client.get("/api/v1/bids/")
        assert response.status_code == 200

    def test_admin_can_list(self, api_client, admin_user, make_bid):
        make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/bids/")
        assert response.status_code == 200

    def test_anonymous_gets_401(self, api_client):
        response = api_client.get("/api/v1/bids/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestBidListBehaviour:
    def test_default_pagination_is_50(self, api_client, viewer, make_bid):
        for _ in range(3):
            make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/")
        assert response.status_code == 200
        assert "results" in response.data
        assert response.data["count"] == 3

    def test_page_size_is_configurable(self, api_client, viewer, make_bid):
        for _ in range(3):
            make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/?page_size=2")
        assert response.status_code == 200
        assert len(response.data["results"]) == 2

    def test_default_date_window_is_today_pm_7_days(self, api_client, viewer, make_bid):
        today = datetime.date.today()
        in_range = make_bid(description="in range", submission_date=today)
        out_of_range = make_bid(description="out of range", submission_date=today - datetime.timedelta(days=30))
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/")
        ids = {row["id"] for row in response.data["results"]}
        assert str(in_range.id) in ids
        assert str(out_of_range.id) not in ids

    def test_explicit_date_window_overrides_default(self, api_client, viewer, make_bid):
        today = datetime.date.today()
        out_of_default_range = make_bid(
            description="old", submission_date=today - datetime.timedelta(days=30)
        )
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(
            "/api/v1/bids/",
            {"submission_after": today - datetime.timedelta(days=40), "submission_before": today},
        )
        ids = {row["id"] for row in response.data["results"]}
        assert str(out_of_default_range.id) in ids

    def test_search_matches_client_name(self, api_client, viewer, make_bid, client_obj):
        today = datetime.date.today()
        make_bid(description="something", submission_date=today)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/", {"search": "Acme"})
        assert response.data["count"] == 1

    def test_stage_filter_is_exact(self, api_client, viewer, make_bid):
        today = datetime.date.today()
        make_bid(description="a", submission_date=today, stage="TENDER")
        make_bid(description="b", submission_date=today, stage="RFP")
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/", {"stage": "TENDER"})
        assert response.data["count"] == 1

    def test_serial_closes_gaps_and_survives_filtering(self, api_client, viewer, make_bid):
        today = datetime.date.today()
        bids = [make_bid(description="x", submission_date=today, stage="TENDER") for _ in range(3)]
        bids[1].is_deleted = True
        bids[1].save()
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/", {"stage": "TENDER"})
        serials = sorted(row["serial"] for row in response.data["results"])
        assert serials == [1, 2]

    def test_team_filter(self, api_client, viewer, make_bid, team):
        today = datetime.date.today()
        make_bid(description="a", submission_date=today, team=team)
        make_bid(description="b", submission_date=today)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/", {"team": team.id})
        assert response.data["count"] == 1
        assert response.data["results"][0]["team"]["id"] == team.id

    def test_engaged_filter(self, api_client, viewer, make_bid):
        today = datetime.date.today()
        person = Person.objects.create(canonical_name="Engaged Person")
        engaged_bid = make_bid(description="a", submission_date=today)
        engaged_bid.engaged_resources.set([person])
        make_bid(description="b", submission_date=today)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/", {"engaged": person.id})
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == str(engaged_bid.id)


@pytest.mark.django_db
class TestBidDetailRoleMatrix:
    def test_viewer_can_retrieve(self, api_client, viewer, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(f"/api/v1/bids/{bid.id}/")
        assert response.status_code == 200
        assert response.data["reference"] == bid.reference
        assert response.data["serial"] == 1
        assert "security_amount_raw" in response.data
        assert "engagement_days" in response.data
        assert "has_unresolved_conflicts" in response.data
        assert response.data["source"] == "app"

    def test_history_is_viewer_accessible(self, api_client, viewer, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(f"/api/v1/bids/{bid.id}/history/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestBidCreateRoleMatrix:
    def create_payload(self, **overrides):
        payload = {
            "client_name": "Brand New Client Ltd",
            "description": "Supply of widgets",
            "submission_date": str(datetime.date.today()),
        }
        payload.update(overrides)
        return payload

    def test_viewer_gets_403(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.post("/api/v1/bids/", self.create_payload(), format="json")
        assert response.status_code == 403

    def test_editor_can_create(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.post("/api/v1/bids/", self.create_payload(), format="json")
        assert response.status_code == 201
        assert response.data["client"]["name"] == "Brand New Client Ltd"
        assert response.data["source"] == "app"

        bid = Bid.objects.get(id=response.data["id"])
        assert bid.created_by_id == editor.id
        assert AuditEntry.objects.filter(bid=bid, action=AuditEntry.Action.BID_CREATE).exists()

    def test_admin_can_create(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post("/api/v1/bids/", self.create_payload(), format="json")
        assert response.status_code == 201

    def test_missing_description_is_rejected(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        payload = self.create_payload()
        payload.pop("description")
        response = api_client.post("/api/v1/bids/", payload, format="json")
        assert response.status_code == 400

    def test_missing_submission_date_is_rejected(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        payload = self.create_payload()
        payload.pop("submission_date")
        response = api_client.post("/api/v1/bids/", payload, format="json")
        assert response.status_code == 400

    def test_stage_and_team_are_optional(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.post("/api/v1/bids/", self.create_payload(), format="json")
        assert response.status_code == 201
        assert response.data["stage"] == ""
        assert response.data["team"] is None


@pytest.mark.django_db
class TestBidUpdateRoleMatrix:
    def test_viewer_gets_403(self, api_client, viewer, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.patch(f"/api/v1/bids/{bid.id}/", {"remarks": "nope"}, format="json")
        assert response.status_code == 403

    def test_editor_update_routes_through_apply_change(self, api_client, editor, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today(), remarks="old")
        login(api_client, editor, "EditorPass123!")
        response = api_client.patch(f"/api/v1/bids/{bid.id}/", {"remarks": "new remarks"}, format="json")
        assert response.status_code == 200
        assert response.data["remarks"] == "new remarks"

        bid.refresh_from_db()
        assert bid.remarks == "new remarks"
        assert "remarks" in bid.locally_overridden
        assert bid.updated_by_id == editor.id
        assert AuditEntry.objects.filter(
            bid=bid, field="remarks", old_value="old", new_value="new remarks"
        ).exists()

    def test_admin_can_update(self, api_client, admin_user, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.patch(f"/api/v1/bids/{bid.id}/", {"remarks": "admin edit"}, format="json")
        assert response.status_code == 200

    def test_unchanged_field_does_not_create_audit_entry(self, api_client, editor, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today(), remarks="same")
        login(api_client, editor, "EditorPass123!")
        api_client.patch(f"/api/v1/bids/{bid.id}/", {"remarks": "same"}, format="json")
        assert not AuditEntry.objects.filter(bid=bid, field="remarks").exists()

    def test_engaged_resources_update_goes_through_apply_change(self, api_client, editor, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today())
        person = Person.objects.create(canonical_name="Jane Analyst")
        login(api_client, editor, "EditorPass123!")
        response = api_client.patch(
            f"/api/v1/bids/{bid.id}/", {"engaged_resources": [person.id]}, format="json"
        )
        assert response.status_code == 200
        bid.refresh_from_db()
        assert list(bid.engaged_resources.values_list("id", flat=True)) == [person.id]
        assert AuditEntry.objects.filter(bid=bid, field="engaged_resources").exists()


@pytest.mark.django_db
class TestBidDeleteRoleMatrix:
    def test_viewer_gets_403(self, api_client, viewer, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.delete(f"/api/v1/bids/{bid.id}/")
        assert response.status_code == 403

    def test_editor_gets_403(self, api_client, editor, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, editor, "EditorPass123!")
        response = api_client.delete(f"/api/v1/bids/{bid.id}/")
        assert response.status_code == 403

    def test_admin_can_soft_delete(self, api_client, admin_user, make_bid):
        bid = make_bid(description="x", submission_date=datetime.date.today())
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.delete(f"/api/v1/bids/{bid.id}/")
        assert response.status_code == 204

        bid.refresh_from_db()
        assert bid.is_deleted is True
        assert AuditEntry.objects.filter(bid=bid, action=AuditEntry.Action.BID_SOFT_DELETE).exists()

        # Soft-deleted bids disappear from the register.
        list_response = api_client.get("/api/v1/bids/")
        ids = {row["id"] for row in list_response.data["results"]}
        assert str(bid.id) not in ids
