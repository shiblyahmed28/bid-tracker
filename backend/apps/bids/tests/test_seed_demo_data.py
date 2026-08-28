import pytest
from django.core.management import call_command

from apps.bids.models import Bid


@pytest.mark.django_db
def test_seed_demo_data_creates_app_sourced_bids():
    call_command("seed_demo_data", "--count", "10")
    demo = Bid.objects.filter(remarks__startswith="[DEMO]")
    assert demo.count() == 10
    assert all(b.source == Bid.Source.APP for b in demo)
    assert all(b.uid is None for b in demo)


@pytest.mark.django_db
def test_seed_demo_data_is_idempotent_on_rerun():
    call_command("seed_demo_data", "--count", "15")
    first_ids = set(Bid.objects.filter(remarks__startswith="[DEMO]").values_list("id", flat=True))

    call_command("seed_demo_data", "--count", "8")
    demo = Bid.objects.filter(remarks__startswith="[DEMO]")
    assert demo.count() == 8
    assert not set(demo.values_list("id", flat=True)) & first_ids


@pytest.mark.django_db
def test_seed_demo_data_never_touches_sheet_sourced_bids(make_bid, client_obj):
    sheet_bid = make_bid(source=Bid.Source.SHEET, submission_date="2026-01-01")
    call_command("seed_demo_data", "--count", "5")
    sheet_bid.refresh_from_db()
    assert sheet_bid.source == Bid.Source.SHEET
    assert Bid.objects.filter(id=sheet_bid.id).exists()
