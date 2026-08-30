"""§Phase 22 items 2-4: the detail page's cost breakdown (engagements +
cost lines + management_cost), the register/dashboard summary-only figure,
the repeatable-row create/edit payload, and the per-bid PDF export."""

import datetime
from decimal import Decimal

import pytest

from apps.audit.models import AuditEntry
from apps.bids.dashboard_views import compute_summary
from apps.bids.models import Bid, BidCostLine, BidEngagement, Person

from conftest import login


@pytest.mark.django_db
class TestBidDetailBreakdown:
    def test_detail_exposes_engagements_cost_lines_and_totals(self, api_client, viewer, make_bid, person):
        bid = make_bid()
        BidEngagement.objects.create(bid=bid, person=person, days=5, convenience_bill=Decimal("1000"))
        BidCostLine.objects.create(bid=bid, description="Printing", amount=Decimal("500"), currency="BDT")
        BidCostLine.objects.create(bid=bid, description="Travel", amount=Decimal("100"), currency="USD")

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(f"/api/v1/bids/{bid.id}/")
        assert response.status_code == 200

        assert len(response.data["engagements"]) == 1
        assert response.data["engagements"][0]["person"]["id"] == person.id
        assert response.data["total_engagement_days"] == 5
        assert response.data["total_convenience_bill"] == Decimal("1000.00")

        cost_lines = response.data["cost_lines"]
        assert len(cost_lines) == 2
        assert {c["line_number"] for c in cost_lines} == {1, 2}
        assert response.data["total_cost_lines"] == {"BDT": Decimal("500.00"), "USD": Decimal("100.00")}
        assert response.data["management_cost"] == {"BDT": Decimal("1500.00"), "USD": Decimal("100.00")}

    def test_detail_with_no_cost_data_is_all_zero(self, api_client, viewer, make_bid):
        bid = make_bid()
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(f"/api/v1/bids/{bid.id}/")
        assert response.data["engagements"] == []
        assert response.data["cost_lines"] == []
        assert response.data["management_cost"] == {"BDT": Decimal("0"), "USD": Decimal("0")}

    def test_line_numbers_follow_date_order(self, api_client, viewer, make_bid):
        bid = make_bid()
        BidCostLine.objects.create(bid=bid, description="later", amount=Decimal("1"), date=datetime.date(2026, 2, 1))
        BidCostLine.objects.create(bid=bid, description="earlier", amount=Decimal("1"), date=datetime.date(2026, 1, 1))
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(f"/api/v1/bids/{bid.id}/")
        by_number = {c["line_number"]: c["description"] for c in response.data["cost_lines"]}
        assert by_number[1] == "earlier"
        assert by_number[2] == "later"


@pytest.mark.django_db
class TestRegisterSummaryFigureOnly:
    """The register/list serializer gets the summary only — never the
    underlying rows (§Phase 22 item 3)."""

    def test_list_exposes_management_cost_summary(self, api_client, viewer, make_bid, person):
        bid = make_bid(submission_date=datetime.date.today())
        BidEngagement.objects.create(bid=bid, person=person, convenience_bill=Decimal("300"))
        BidCostLine.objects.create(bid=bid, description="x", amount=Decimal("200"), currency="BDT")

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/bids/")
        row = next(r for r in response.data["results"] if r["id"] == str(bid.id))
        assert row["management_cost_bdt"] == Decimal("500.00")
        assert row["management_cost_usd"] == Decimal("0")
        assert "engagements" not in row
        assert "cost_lines" not in row


@pytest.mark.django_db
class TestEngagementAndCostLineWritePayload:
    def create_payload(self, **overrides):
        payload = {
            "client_name": "Cost Breakdown Client",
            "description": "test",
            "submission_date": str(datetime.date.today()),
        }
        payload.update(overrides)
        return payload

    def test_create_with_engagements_and_cost_lines(self, api_client, editor, person):
        login(api_client, editor, "EditorPass123!")
        response = api_client.post(
            "/api/v1/bids/",
            self.create_payload(
                engagements=[{"person": person.id, "days": 3, "convenience_bill": "500"}],
                cost_lines=[{"description": "Printing", "amount": "200"}],
            ),
            format="json",
        )
        assert response.status_code == 201
        assert response.data["total_engagement_days"] == 3
        assert response.data["total_cost_lines"] == {"BDT": Decimal("200.00"), "USD": Decimal("0")}
        assert [p["id"] for p in response.data["engaged_resources"]] == [person.id]

    def test_update_engagement_detail_only_change_still_audits_without_membership_change(
        self, api_client, editor, make_bid, person
    ):
        bid = make_bid()
        engagement = BidEngagement.objects.create(bid=bid, person=person, days=3)
        login(api_client, editor, "EditorPass123!")

        response = api_client.patch(
            f"/api/v1/bids/{bid.id}/",
            {"engagements": [{"person": person.id, "days": 9}]},
            format="json",
        )
        assert response.status_code == 200
        engagement.refresh_from_db()
        assert engagement.days == 9
        assert engagement.id == engagement.pk  # same row, keyed by person — not delete+recreate
        assert AuditEntry.objects.filter(bid=bid, field="engagements").exists()

    def test_update_removes_stale_engagement_rows(self, api_client, editor, make_bid, person):
        bid = make_bid()
        other_person = Person.objects.create(canonical_name="Other Person")
        BidEngagement.objects.create(bid=bid, person=person)
        BidEngagement.objects.create(bid=bid, person=other_person)

        login(api_client, editor, "EditorPass123!")
        response = api_client.patch(
            f"/api/v1/bids/{bid.id}/", {"engagements": [{"person": person.id}]}, format="json"
        )
        assert response.status_code == 200
        assert list(BidEngagement.objects.filter(bid=bid).values_list("person_id", flat=True)) == [person.id]

    def test_update_replaces_cost_lines_and_audits(self, api_client, editor, make_bid):
        bid = make_bid()
        old_line = BidCostLine.objects.create(bid=bid, description="Old", amount=Decimal("100"))
        login(api_client, editor, "EditorPass123!")

        response = api_client.patch(
            f"/api/v1/bids/{bid.id}/",
            {"cost_lines": [{"description": "New", "amount": "250"}]},
            format="json",
        )
        assert response.status_code == 200
        assert not BidCostLine.objects.filter(pk=old_line.pk).exists()
        remaining = BidCostLine.objects.get(bid=bid)
        assert remaining.description == "New"
        assert AuditEntry.objects.filter(bid=bid, field="cost_lines").exists()

    def test_update_with_identical_cost_lines_does_not_audit(self, api_client, editor, make_bid):
        bid = make_bid()
        BidCostLine.objects.create(bid=bid, description="Same", amount=Decimal("100"), currency="BDT")
        login(api_client, editor, "EditorPass123!")

        AuditEntry.objects.filter(bid=bid).delete()
        response = api_client.patch(
            f"/api/v1/bids/{bid.id}/",
            {"cost_lines": [{"description": "Same", "amount": "100", "currency": "BDT"}]},
            format="json",
        )
        assert response.status_code == 200
        assert not AuditEntry.objects.filter(bid=bid, field="cost_lines").exists()

    def test_removing_all_cost_lines_via_empty_list(self, api_client, editor, make_bid):
        bid = make_bid()
        BidCostLine.objects.create(bid=bid, description="Gone", amount=Decimal("100"))
        login(api_client, editor, "EditorPass123!")
        response = api_client.patch(f"/api/v1/bids/{bid.id}/", {"cost_lines": []}, format="json")
        assert response.status_code == 200
        assert not BidCostLine.objects.filter(bid=bid).exists()

    def test_negative_amount_is_rejected(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.post(
            "/api/v1/bids/",
            self.create_payload(cost_lines=[{"description": "x", "amount": "-50"}]),
            format="json",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestRegisterExportManagementCostColumn:
    """§Phase 22 item 3 — the register CSV/PDF export can include the same
    summary-only management_cost column as the live table, mirroring
    frontend/src/register/columns.tsx per export_columns.py's own header."""

    def test_csv_export_includes_management_cost_column(self, api_client, viewer, make_bid, person):
        bid = make_bid(submission_date=datetime.date.today())
        BidEngagement.objects.create(bid=bid, person=person, convenience_bill=Decimal("300"))
        BidCostLine.objects.create(bid=bid, description="x", amount=Decimal("200"), currency="BDT")

        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(
            "/api/v1/bids/export/csv/",
            {"columns": "client,management_cost", "submission_after": "2000-01-01", "submission_before": "2100-01-01"},
        )
        assert response.status_code == 200
        body = b"".join(response.streaming_content).decode("utf-8-sig")
        assert bid.client.name in body
        assert "500.00" in body


@pytest.mark.django_db
class TestBidDetailPdfExport:
    def test_viewer_with_export_pdf_capability_can_export(self, api_client, viewer, make_bid):
        bid = make_bid()
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get(f"/api/v1/bids/{bid.id}/export/pdf/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_anonymous_gets_401(self, api_client, make_bid):
        bid = make_bid()
        response = api_client.get(f"/api/v1/bids/{bid.id}/export/pdf/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestDashboardManagementCostSummary:
    def test_compute_summary_includes_management_cost(self, client_obj, person):
        bid = Bid.objects.create(
            client=client_obj, description="x", submission_date=datetime.date(2026, 9, 10)
        )
        BidEngagement.objects.create(bid=bid, person=person, convenience_bill=Decimal("300"))
        BidCostLine.objects.create(bid=bid, description="x", amount=Decimal("200"), currency="BDT")
        BidCostLine.objects.create(bid=bid, description="y", amount=Decimal("50"), currency="USD")

        summary = compute_summary(datetime.date(2026, 9, 1), datetime.date(2026, 9, 30))
        assert summary["management_cost"] == {"BDT": Decimal("500"), "USD": Decimal("50")}

    def test_never_sums_bdt_and_usd_together(self, client_obj, person):
        bid = Bid.objects.create(
            client=client_obj, description="x", submission_date=datetime.date(2026, 9, 10)
        )
        BidCostLine.objects.create(bid=bid, description="x", amount=Decimal("100"), currency="USD")
        summary = compute_summary(datetime.date(2026, 9, 1), datetime.date(2026, 9, 30))
        assert summary["management_cost"]["BDT"] == Decimal("0")
        assert summary["management_cost"]["USD"] == Decimal("100")

    def test_two_engagements_two_cost_lines_does_not_double_count(self, client_obj, person):
        """Regression guard: aggregating cost_lines and engagements in one
        combined query would fan out and double-count when a bid has more
        than one row on each side."""
        bid = Bid.objects.create(
            client=client_obj, description="x", submission_date=datetime.date(2026, 9, 10)
        )
        other_person = Person.objects.create(canonical_name="Second Person")
        BidEngagement.objects.create(bid=bid, person=person, convenience_bill=Decimal("100"))
        BidEngagement.objects.create(bid=bid, person=other_person, convenience_bill=Decimal("100"))
        BidCostLine.objects.create(bid=bid, description="a", amount=Decimal("50"), currency="BDT")
        BidCostLine.objects.create(bid=bid, description="b", amount=Decimal("50"), currency="BDT")

        summary = compute_summary(datetime.date(2026, 9, 1), datetime.date(2026, 9, 30))
        assert summary["management_cost"]["BDT"] == Decimal("300")  # 200 convenience + 100 cost lines
