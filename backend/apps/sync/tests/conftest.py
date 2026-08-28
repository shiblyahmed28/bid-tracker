import pytest

from apps.bids.models import Client


@pytest.fixture
def client_obj(db):
    return Client.objects.create(name="Acme Corp", canonical_name="acme corp")


@pytest.fixture
def make_bid(db, client_obj):
    import datetime

    from apps.bids.models import Bid

    def _make_bid(**kwargs):
        kwargs.setdefault("client", client_obj)
        kwargs.setdefault("description", "x")
        kwargs.setdefault("submission_date", datetime.date.today())
        return Bid.objects.create(**kwargs)

    return _make_bid
