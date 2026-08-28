import datetime

import pytest

from conftest import login

TODAY = datetime.date.today()


@pytest.mark.django_db
class TestDistinctValuesRoleMatrix:
    def test_viewer_can_access(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/distinct/", {"field": "stage"})
        assert response.status_code == 200

    def test_anonymous_gets_401(self, api_client):
        response = api_client.get("/api/v1/bids/distinct/", {"field": "stage"})
        assert response.status_code == 401


@pytest.mark.django_db
class TestDistinctValuesContent:
    def test_plain_text_field_is_sorted_and_deduped(self, api_client, viewer, make_bid):
        make_bid(description="a", submission_date=TODAY, stage="TENDER")
        make_bid(description="b", submission_date=TODAY, stage="TENDER")
        make_bid(description="c", submission_date=TODAY, stage="RFP")
        make_bid(description="d", submission_date=TODAY, stage="")

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/distinct/", {"field": "stage"})
        values = [row["value"] for row in response.data["options"]]
        assert values == ["RFP", "TENDER"]

    def test_is_unscoped_by_date_range(self, api_client, viewer, make_bid):
        make_bid(description="old", submission_date=TODAY - datetime.timedelta(days=1000), stage="EOI")

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/distinct/", {"field": "stage"})
        assert "EOI" in [row["value"] for row in response.data["options"]]

    def test_team_returns_id_value_and_name_label(self, api_client, viewer, team):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/distinct/", {"field": "team"})
        row = next(r for r in response.data["options"] if r["label"] == team.name)
        assert row["value"] == str(team.id)

    def test_delivery_type_combines_the_three_booleans(self, api_client, viewer, make_bid):
        make_bid(description="a", submission_date=TODAY, is_goods=True, is_service=True)
        make_bid(description="b", submission_date=TODAY, is_works=True)

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/distinct/", {"field": "delivery_type"})
        values = {row["value"] for row in response.data["options"]}
        assert "Goods, Service" in values
        assert "Works" in values

    def test_unknown_field_is_rejected(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/distinct/", {"field": "nonsense"})
        assert response.status_code == 400
