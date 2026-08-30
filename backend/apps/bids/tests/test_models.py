import datetime
from decimal import Decimal

import pytest

from apps.audit.models import AuditEntry
from apps.bids.models import Bid, BidCostLine, BidEngagement, Person


@pytest.mark.django_db
def test_reference_is_generated_on_create(make_bid):
    bid = make_bid()
    year = datetime.date.today().year
    assert bid.reference == f"SPC-{year}-{bid.arrival_seq:04d}"


@pytest.mark.django_db
def test_reference_is_permanent_once_set(make_bid):
    bid = make_bid()
    original_reference = bid.reference
    bid.remarks = "changed"
    bid.save()
    bid.refresh_from_db()
    assert bid.reference == original_reference


@pytest.mark.django_db
def test_arrival_seq_is_unique_and_monotonic(make_bid):
    first = make_bid()
    second = make_bid()
    assert second.arrival_seq > first.arrival_seq


@pytest.mark.django_db
def test_serial_closes_gaps_after_delete(make_bid):
    bids = [make_bid() for _ in range(5)]

    third = bids[2]
    third.is_deleted = True
    third.save()

    serials = {b.id: b.serial for b in Bid.objects.with_serial()}

    remaining = [b for b in bids if b.id != third.id]
    assert sorted(serials.values()) == [1, 2, 3, 4]
    assert third.id not in serials
    for expected_serial, bid in enumerate(remaining, start=1):
        assert serials[bid.id] == expected_serial


@pytest.mark.django_db
def test_soft_delete_hides_from_default_manager(make_bid):
    bid = make_bid()
    bid.is_deleted = True
    bid.save()

    assert not Bid.objects.filter(id=bid.id).exists()
    assert Bid.all_objects.filter(id=bid.id).exists()


@pytest.mark.django_db
def test_apply_change_by_human_marks_locally_overridden_and_audits(make_bid, editor):
    bid = make_bid(remarks="old remarks")

    bid.apply_change("remarks", "new remarks", actor=editor)
    bid.refresh_from_db()

    assert bid.remarks == "new remarks"
    assert "remarks" in bid.locally_overridden

    entry = AuditEntry.objects.get(bid=bid, field="remarks")
    assert entry.actor == editor
    assert entry.actor_label == ""
    assert entry.old_value == "old remarks"
    assert entry.new_value == "new remarks"
    assert entry.action == AuditEntry.Action.BID_UPDATE


@pytest.mark.django_db
def test_apply_change_by_system_does_not_mark_locally_overridden(make_bid):
    bid = make_bid(remarks="old remarks")

    bid.apply_change("remarks", "sheet remarks", actor=None)
    bid.refresh_from_db()

    assert bid.remarks == "sheet remarks"
    assert "remarks" not in bid.locally_overridden

    entry = AuditEntry.objects.get(bid=bid, field="remarks")
    assert entry.actor is None
    assert entry.actor_label == "System (sync)"


@pytest.mark.django_db
def test_engagement_days_computed_from_date_pair(make_bid):
    bid = make_bid(
        engagement_from=datetime.date(2026, 1, 1),
        engagement_to=datetime.date(2026, 1, 11),
    )
    assert bid.engagement_days == 10


@pytest.mark.django_db
def test_engagement_days_is_not_a_database_column(make_bid):
    bid = make_bid()
    assert "engagement_days" not in [f.name for f in Bid._meta.get_fields()]


@pytest.mark.django_db
def test_engagement_days_none_without_full_pair(make_bid):
    bid = make_bid(engagement_from=datetime.date(2026, 1, 1))
    assert bid.engagement_days is None


@pytest.mark.django_db
class TestEngagementAndCostTotals:
    """§Phase 19 item 3 — all computed from BidEngagement/BidCostLine, none
    stored on Bid."""

    def test_days_is_independent_of_the_engaged_date_span(self, make_bid, person):
        """Someone engaged 1-15 Aug may have worked 7 days — `days` is entered
        directly, never derived from (engaged_to - engaged_from)."""
        bid = make_bid()
        BidEngagement.objects.create(
            bid=bid,
            person=person,
            engaged_from=datetime.date(2026, 8, 1),
            engaged_to=datetime.date(2026, 8, 15),
            days=7,
        )
        assert bid.total_engagement_days == 7

    def test_totals_compute_correctly_across_multiple_rows(self, make_bid, person):
        bid = make_bid()
        other_person = Person.objects.create(canonical_name="Imran Kabir")
        BidEngagement.objects.create(bid=bid, person=person, days=5, convenience_bill=Decimal("1000"))
        BidEngagement.objects.create(bid=bid, person=other_person, days=3, convenience_bill=Decimal("500"))
        BidCostLine.objects.create(bid=bid, description="Printing", amount=Decimal("200"), currency="BDT")
        BidCostLine.objects.create(bid=bid, description="Courier", amount=Decimal("50"), currency="USD")

        assert bid.total_engagement_days == 8
        assert bid.total_convenience_bill == Decimal("1500")
        assert bid.total_cost_lines == {"BDT": Decimal("200"), "USD": Decimal("50")}
        # convenience_bill is always BDT (§Phase 19 item 1) — only the BDT
        # side of management_cost gets it added.
        assert bid.management_cost == {"BDT": Decimal("1700"), "USD": Decimal("50")}

    def test_totals_are_zero_not_none_with_no_rows(self, make_bid):
        bid = make_bid()
        assert bid.total_engagement_days == 0
        assert bid.total_convenience_bill == Decimal("0")
        assert bid.total_cost_lines == {"BDT": Decimal("0"), "USD": Decimal("0")}
        assert bid.management_cost == {"BDT": Decimal("0"), "USD": Decimal("0")}

    def test_deleting_a_cost_line_changes_management_cost(self, make_bid):
        bid = make_bid()
        keep = BidCostLine.objects.create(bid=bid, description="Printing", amount=Decimal("200"), currency="BDT")
        BidCostLine.objects.create(bid=bid, description="Travel", amount=Decimal("300"), currency="BDT")

        assert bid.management_cost["BDT"] == Decimal("500")

        BidCostLine.objects.exclude(pk=keep.pk).delete()
        assert bid.management_cost["BDT"] == Decimal("200")

    def test_never_sums_bdt_and_usd_together(self, make_bid):
        bid = make_bid()
        BidCostLine.objects.create(bid=bid, description="A", amount=Decimal("100"), currency="BDT")
        BidCostLine.objects.create(bid=bid, description="B", amount=Decimal("100"), currency="USD")
        totals = bid.total_cost_lines
        assert totals["BDT"] == Decimal("100")
        assert totals["USD"] == Decimal("100")


@pytest.mark.django_db
class TestBidEngagementThroughModel:
    def test_existing_engaged_resources_api_still_works(self, make_bid, person):
        """engaged_resources is still read/written as a plain Person list —
        only the underlying table gained extra columns (§Phase 19 item 1)."""
        bid = make_bid()
        other_person = Person.objects.create(canonical_name="Nusrat Jahan")

        bid.engaged_resources.set([person, other_person])
        assert set(bid.engaged_resources.all()) == {person, other_person}

        # The through row got created with the documented defaults.
        engagement = BidEngagement.objects.get(bid=bid, person=person)
        assert engagement.days == 0
        assert engagement.convenience_bill == Decimal("0")
        assert engagement.engaged_from is None

    def test_apply_change_on_engaged_resources_still_audits(self, make_bid, person, editor):
        bid = make_bid()
        bid.apply_change("engaged_resources", [person], actor=editor)
        assert list(bid.engaged_resources.all()) == [person]
        entry = AuditEntry.objects.get(bid=bid, field="engaged_resources")
        assert person.canonical_name in entry.new_value

    def test_unique_together_bid_person(self, make_bid, person):
        from django.db import IntegrityError, transaction

        bid = make_bid()
        BidEngagement.objects.create(bid=bid, person=person)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                BidEngagement.objects.create(bid=bid, person=person)


@pytest.mark.django_db
class TestPersonNewFields:
    """§Phase 19 item 4."""

    def test_defaults(self):
        person = Person.objects.create(canonical_name="Default Person")
        assert person.person_type == Person.PersonType.INTERNAL
        assert person.is_active is True
        assert person.email is None

    def test_email_is_optional_multiple_people_may_have_none(self):
        Person.objects.create(canonical_name="No Email One")
        Person.objects.create(canonical_name="No Email Two")
        assert Person.objects.filter(email__isnull=True).count() == 2

    def test_email_is_unique_when_set(self):
        Person.objects.create(canonical_name="Has Email One", email="a@example.com")
        with pytest.raises(Exception):
            Person.objects.create(canonical_name="Has Email Two", email="a@example.com")

    def test_user_links_to_a_login_account(self, editor):
        person = Person.objects.create(canonical_name="Linked Person", user=editor)
        assert person.user == editor
        assert editor.person_profile == person


@pytest.mark.django_db
class TestBidCostLineNumbers:
    def test_line_numbers_follow_date_order_not_insertion_order(self, make_bid):
        bid = make_bid()
        third = BidCostLine.objects.create(bid=bid, description="third", amount=Decimal("1"), date=datetime.date(2026, 1, 3))
        first = BidCostLine.objects.create(bid=bid, description="first", amount=Decimal("1"), date=datetime.date(2026, 1, 1))
        second = BidCostLine.objects.create(bid=bid, description="second", amount=Decimal("1"), date=datetime.date(2026, 1, 2))

        numbered = {row.pk: row.line_number for row in BidCostLine.objects.with_line_number().filter(bid=bid)}
        assert numbered[first.pk] == 1
        assert numbered[second.pk] == 2
        assert numbered[third.pk] == 3

    def test_line_number_is_not_a_database_column(self):
        assert "line_number" not in [f.name for f in BidCostLine._meta.get_fields()]

    def test_line_numbers_are_scoped_per_bid(self, make_bid):
        bid_a = make_bid()
        bid_b = make_bid()
        BidCostLine.objects.create(bid=bid_a, description="a1", amount=Decimal("1"), date=datetime.date(2026, 1, 1))
        only_line_b = BidCostLine.objects.create(
            bid=bid_b, description="b1", amount=Decimal("1"), date=datetime.date(2026, 1, 1)
        )

        numbered = {row.pk: row.line_number for row in BidCostLine.objects.with_line_number().filter(bid=bid_b)}
        assert numbered[only_line_b.pk] == 1
