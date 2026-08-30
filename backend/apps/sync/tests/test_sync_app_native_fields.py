"""§Phase 19 item 6: sync must never touch BidEngagement, BidCostLine, or the
new Person fields — they're app-native, same as team/engaged_resources/
engagement dates were already (§9 step 4d). run_sync() is exercised for real
here (sheet I/O mocked), against an existing bid that already carries all of
these, to prove the sync leaves them alone while still updating a genuine
sheet-owned field.
"""

import datetime
import uuid
from decimal import Decimal

import pytest

from apps.bids.models import Bid, BidCostLine, BidEngagement, Person
from apps.sync.sync import run_sync

HEADER_ROW = [""] * 29 + ["uid"]  # uid at index 29; other headers unused (columns addressed by index, §5)


def _row(uid_value, client_name="Acme Corp", stage="RFP", submission_date="2026-09-01"):
    row = [""] * 30
    row[1] = client_name
    row[2] = "a description"
    row[7] = stage
    row[18] = submission_date
    row[29] = uid_value
    return row


@pytest.fixture
def fake_sheet_io(monkeypatch):
    """Bypasses the real Google Sheets client entirely — get_client/
    get_worksheet return a stub whose only used method is row_values(),
    and read_data_rows is monkeypatched directly to hand back canned rows."""

    class FakeWorksheet:
        def row_values(self, n):
            return HEADER_ROW

        def batch_update(self, data):
            raise AssertionError("uid backfill should not run when every row already has a uid")

    def _install(rows):
        monkeypatch.setattr("apps.sync.sync.get_client", lambda: object())
        monkeypatch.setattr("apps.sync.sync.get_worksheet", lambda client: FakeWorksheet())
        monkeypatch.setattr("apps.sync.sync.read_data_rows", lambda worksheet: rows)

    return _install


@pytest.mark.django_db
def test_sync_leaves_engagement_cost_and_person_fields_untouched(fake_sheet_io, client_obj):
    existing_uid = uuid.uuid4()
    bid = Bid.objects.create(
        uid=existing_uid,
        source=Bid.Source.SHEET,
        client=client_obj,
        description="a description",
        stage="TENDER",  # sheet will say RFP — proves the sync actually ran
        submission_date=datetime.date(2026, 9, 1),
    )

    person = Person.objects.create(
        canonical_name="Farhana Islam",
        email="farhana@example.com",
        person_type=Person.PersonType.EXTERNAL,
        organization="Partner Co",
        welcome_email_sent_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    )
    engagement = BidEngagement.objects.create(
        bid=bid, person=person, days=9, convenience_bill=Decimal("4500"), note="handled procurement"
    )
    cost_line = BidCostLine.objects.create(
        bid=bid, description="Printing", amount=Decimal("300"), currency="BDT", category="Printing"
    )

    fake_sheet_io([(4, _row(str(existing_uid)))])
    sync_run, counts = run_sync(trigger="manual")

    bid.refresh_from_db()
    engagement.refresh_from_db()
    cost_line.refresh_from_db()
    person.refresh_from_db()

    # Proves the sync did real work (a sheet-owned field changed) rather than
    # short-circuiting before touching anything.
    assert counts["updated"] == 1
    assert bid.stage == "RFP"

    assert BidEngagement.objects.filter(pk=engagement.pk).exists()
    assert engagement.days == 9
    assert engagement.convenience_bill == Decimal("4500")
    assert engagement.note == "handled procurement"

    assert BidCostLine.objects.filter(pk=cost_line.pk).exists()
    assert cost_line.amount == Decimal("300")
    assert cost_line.category == "Printing"

    assert person.email == "farhana@example.com"
    assert person.person_type == Person.PersonType.EXTERNAL
    assert person.organization == "Partner Co"
    assert person.welcome_email_sent_at is not None
