import datetime
from decimal import Decimal

import pytest

from conftest import login

TODAY = datetime.date.today()

DASHBOARD_ENDPOINTS = [
    "/api/v1/dashboard/summary/",
    "/api/v1/dashboard/trend/",
    "/api/v1/dashboard/breakdown/",
    "/api/v1/dashboard/deadlines/",
    "/api/v1/dashboard/bg-exposure/",
    "/api/v1/dashboard/classic/",
]


@pytest.mark.django_db
class TestDashboardRoleMatrix:
    @pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
    def test_viewer_can_access(self, api_client, viewer, endpoint):
        login(api_client, viewer, "ViewerPass123!")
        assert api_client.get(endpoint).status_code == 200

    @pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
    def test_editor_can_access(self, api_client, editor, endpoint):
        login(api_client, editor, "EditorPass123!")
        assert api_client.get(endpoint).status_code == 200

    @pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
    def test_admin_can_access(self, api_client, admin_user, endpoint):
        login(api_client, admin_user, "AdminPass123!")
        assert api_client.get(endpoint).status_code == 200

    @pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
    def test_anonymous_gets_401(self, api_client, endpoint):
        assert api_client.get(endpoint).status_code == 401


@pytest.mark.django_db
class TestDashboardSummary:
    def test_counts_and_bdt_usd_stay_separate(self, api_client, viewer, make_bid):
        make_bid(
            description="won bdt",
            submission_date=TODAY,
            submission_status="SUBMITTED",
            result="WON",
            security_amount=Decimal("100000"),
            security_currency="BDT",
        )
        make_bid(
            description="lost usd",
            submission_date=TODAY,
            submission_status="SUBMITTED",
            result="LOST",
            security_amount=Decimal("5000"),
            security_currency="USD",
        )
        make_bid(
            description="pending",
            submission_date=TODAY,
            submission_status="NOT SUBMITTED",
            result="PENDING",
        )

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/dashboard/summary/")
        assert response.status_code == 200
        data = response.data

        assert data["total"] == 3
        assert data["submitted"] == 2
        assert data["not_submitted"] == 1
        assert data["won"] == 1
        assert data["lost"] == 1
        assert data["pending"] == 1
        assert Decimal(str(data["security_locked"]["BDT"])) == Decimal("100000")
        assert Decimal(str(data["security_locked"]["USD"])) == Decimal("5000")

    def test_respects_from_to(self, api_client, viewer, make_bid):
        make_bid(description="in", submission_date=TODAY)
        make_bid(description="out", submission_date=TODAY - datetime.timedelta(days=100))

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(
            "/api/v1/dashboard/summary/",
            {"from": str(TODAY - datetime.timedelta(days=1)), "to": str(TODAY + datetime.timedelta(days=1))},
        )
        assert response.data["total"] == 1


@pytest.mark.django_db
class TestDashboardTrendAdaptiveBucketing:
    def test_daily_for_a_15_day_span(self, api_client, viewer, make_bid):
        make_bid(description="x", submission_date=TODAY)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(
            "/api/v1/dashboard/trend/",
            {"from": str(TODAY), "to": str(TODAY + datetime.timedelta(days=15))},
        )
        assert response.status_code == 200
        assert response.data["bucket"] == "daily"

    def test_quarterly_for_a_5_year_span(self, api_client, viewer, make_bid):
        make_bid(description="x", submission_date=TODAY)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(
            "/api/v1/dashboard/trend/", {"from": "2021-01-01", "to": "2026-01-01"}
        )
        assert response.status_code == 200
        assert response.data["bucket"] == "quarterly"

    def test_monthly_for_a_200_day_span(self, api_client, viewer, make_bid):
        make_bid(description="x", submission_date=TODAY)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(
            "/api/v1/dashboard/trend/",
            {"from": str(TODAY - datetime.timedelta(days=100)), "to": str(TODAY + datetime.timedelta(days=100))},
        )
        assert response.data["bucket"] == "monthly"


@pytest.mark.django_db
class TestDashboardBreakdown:
    def test_by_team(self, api_client, viewer, make_bid, team):
        make_bid(description="a", submission_date=TODAY, team=team)
        make_bid(description="b", submission_date=TODAY, team=team)
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/dashboard/breakdown/", {"by": "team"})
        assert response.status_code == 200
        rows = {row["label"]: row["count"] for row in response.data["breakdown"]}
        assert rows[team.name] == 2

    def test_invalid_by_is_rejected(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/dashboard/breakdown/", {"by": "nonsense"})
        assert response.status_code == 400


@pytest.mark.django_db
class TestDashboardBgExposure:
    def test_only_lists_bids_expiring_within_days(self, api_client, viewer, make_bid):
        make_bid(
            description="expiring soon", submission_date=TODAY, bg_expiry_date=TODAY + datetime.timedelta(days=10)
        )
        make_bid(
            description="expiring later", submission_date=TODAY, bg_expiry_date=TODAY + datetime.timedelta(days=200)
        )
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/dashboard/bg-exposure/", {"days": 60})
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["items"][0]["reference"]
