import datetime

import pytest

from conftest import login

TODAY = datetime.date.today()


@pytest.mark.django_db
class TestRegisterBreakdownRoleMatrix:
    def test_viewer_can_access(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/breakdown/", {"by": "client"})
        assert response.status_code == 200

    def test_anonymous_gets_401(self, api_client):
        response = api_client.get("/api/v1/bids/breakdown/", {"by": "client"})
        assert response.status_code == 401

    def test_invalid_by_is_rejected(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/breakdown/", {"by": "not_a_field"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestRegisterBreakdownContent:
    def test_groups_by_client_name(self, api_client, viewer, make_bid, client_obj):
        make_bid(description="a", submission_date=TODAY)
        make_bid(description="b", submission_date=TODAY)
        login(api_client, viewer, "ViewerPass123!")

        response = api_client.get("/api/v1/bids/breakdown/", {"by": "client"})
        assert response.data["by"] == "client"
        row = next(r for r in response.data["breakdown"] if r["label"] == client_obj.name)
        assert row["count"] == 2

    def test_supports_submission_status(self, api_client, viewer, make_bid):
        make_bid(description="a", submission_date=TODAY, submission_status="SUBMITTED")
        make_bid(description="b", submission_date=TODAY, submission_status="NOT SUBMITTED")
        login(api_client, viewer, "ViewerPass123!")

        response = api_client.get("/api/v1/bids/breakdown/", {"by": "submission_status"})
        labels = {r["label"]: r["count"] for r in response.data["breakdown"]}
        assert labels == {"SUBMITTED": 1, "NOT SUBMITTED": 1}

    def test_respects_non_date_register_filters(self, api_client, viewer, make_bid):
        """The whole point of this endpoint vs. /dashboard/breakdown/: a
        register filter like `stage` must narrow the grouped counts, not
        just the shared date range."""
        make_bid(description="a", submission_date=TODAY, stage="TENDER")
        make_bid(description="b", submission_date=TODAY, stage="RFP")
        login(api_client, viewer, "ViewerPass123!")

        response = api_client.get("/api/v1/bids/breakdown/", {"by": "result", "stage": "TENDER"})
        assert sum(r["count"] for r in response.data["breakdown"]) == 1

    def test_respects_search(self, api_client, viewer, make_bid, client_obj):
        make_bid(description="alpha widget", submission_date=TODAY)
        make_bid(description="beta gadget", submission_date=TODAY)
        login(api_client, viewer, "ViewerPass123!")

        response = api_client.get("/api/v1/bids/breakdown/", {"by": "client", "search": "alpha"})
        assert sum(r["count"] for r in response.data["breakdown"]) == 1

    def test_ignores_default_seven_day_window_when_dates_omitted(self, api_client, viewer, make_bid):
        """Unlike /bids/, this endpoint (like PDF/CSV export) applies no
        implicit date window — the caller (the register) always supplies
        the shared range explicitly."""
        make_bid(description="old", submission_date=TODAY - datetime.timedelta(days=1000))
        login(api_client, viewer, "ViewerPass123!")

        response = api_client.get("/api/v1/bids/breakdown/", {"by": "result"})
        assert sum(r["count"] for r in response.data["breakdown"]) == 1
