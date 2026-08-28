import datetime

import pytest

from apps.audit.models import AuditEntry
from apps.bids.models import Bid


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
