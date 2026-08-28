import pytest

from apps.bids.models import Person

from conftest import login


@pytest.mark.django_db
class TestPersonList:
    def test_viewer_can_list(self, api_client, viewer):
        Person.objects.create(canonical_name="Zed Person")
        Person.objects.create(canonical_name="Aardvark Person")
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/people/")
        assert response.status_code == 200
        names = [p["canonical_name"] for p in response.data]
        assert names == sorted(names)
        assert "Aardvark Person" in names

    def test_anonymous_gets_401(self, api_client):
        response = api_client.get("/api/v1/people/")
        assert response.status_code == 401

    def test_is_unpaginated(self, api_client, viewer):
        for i in range(5):
            Person.objects.create(canonical_name=f"Person {i}")
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/people/")
        assert isinstance(response.data, list)
