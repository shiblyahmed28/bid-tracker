import pytest

from apps.accounts.models import User
from apps.bids.models import Client, Person, Team


@pytest.fixture
def editor(db):
    return User.objects.create_user(
        email="editor@spectrum-bd.com", password="EditorPass123!", role=User.Role.EDITOR
    )


@pytest.fixture
def client_obj(db):
    return Client.objects.create(name="Acme Corp", canonical_name="acme corp")


@pytest.fixture
def team(db):
    return Team.objects.get(name="Government")


@pytest.fixture
def person(db):
    return Person.objects.create(canonical_name="Farhana Islam")


@pytest.fixture
def make_bid(db, client_obj):
    from apps.bids.models import Bid

    def _make_bid(**kwargs):
        kwargs.setdefault("client", client_obj)
        return Bid.objects.create(**kwargs)

    return _make_bid
