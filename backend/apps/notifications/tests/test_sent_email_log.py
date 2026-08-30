"""§Phase 21 items 2 and 4: expanded email content (CAM, bid manager, team,
published date, delivery type) and the SentEmail delivery log."""

import pytest
from django.core import mail

from apps.bids.models import Bid, Client, Person, Team
from apps.notifications.emails import send_deadline_email, send_new_bid_email, send_policy_event_email
from apps.notifications.models import SentEmail
from apps.settings_admin.models import NotificationPolicy

from conftest import login


@pytest.fixture
def client_obj(db):
    return Client.objects.create(name="Acme Corp", canonical_name="acme corp")


@pytest.fixture
def rich_bid(db, client_obj):
    team = Team.objects.get(name="Government")  # seeded by bids.0002_seed_teams
    cam = Person.objects.create(canonical_name="Cam Person")
    bid_manager = Person.objects.create(canonical_name="Manager Person")
    return Bid.objects.create(
        client=client_obj,
        description="a rich bid",
        submission_date="2026-09-10",
        published_date="2026-08-01",
        team=team,
        cam=cam,
        bid_manager=bid_manager,
        is_goods=True,
        is_service=True,
    )


@pytest.mark.django_db
class TestExpandedEmailContent:
    def _assert_expanded_fields_present(self, sent):
        for body in [sent.body] + [alt for alt, _mimetype in sent.alternatives]:
            assert "Government" in body
            assert "Cam Person" in body
            assert "Manager Person" in body
            assert "2026-08-01" in body
            assert "Goods, Service" in body

    def test_new_bid_email_includes_expanded_fields(self, viewer, rich_bid):
        mail.outbox = []
        send_new_bid_email(viewer, rich_bid)
        assert len(mail.outbox) == 1
        self._assert_expanded_fields_present(mail.outbox[0])

    def test_deadline_email_includes_expanded_fields(self, viewer, rich_bid):
        mail.outbox = []
        send_deadline_email(viewer, rich_bid, days_before=7)
        assert len(mail.outbox) == 1
        self._assert_expanded_fields_present(mail.outbox[0])

    def test_policy_event_email_includes_expanded_fields(self, viewer, rich_bid):
        policy = NotificationPolicy.objects.get(event_key="result_won")  # seeded by settings_admin.0002
        mail.outbox = []
        send_policy_event_email(viewer, rich_bid, policy)
        assert len(mail.outbox) == 1
        self._assert_expanded_fields_present(mail.outbox[0])

    def test_delivery_type_display_with_no_flags_set(self, client_obj):
        bid = Bid.objects.create(client=client_obj, description="x", submission_date="2026-09-10")
        assert bid.delivery_type_display == "—"


@pytest.mark.django_db
class TestSentEmailLogging:
    def test_successful_send_is_logged(self, viewer, rich_bid):
        SentEmail.objects.all().delete()
        send_new_bid_email(viewer, rich_bid)
        entry = SentEmail.objects.get()
        assert entry.to_email == viewer.email
        assert entry.kind == SentEmail.Kind.NEW_BID
        assert entry.bid_id == rich_bid.id
        assert entry.success is True
        assert entry.error == ""

    def test_never_logs_a_message_body(self, viewer, rich_bid):
        send_new_bid_email(viewer, rich_bid)
        entry = SentEmail.objects.latest("created_at")
        assert not hasattr(entry, "body")
        assert "body" not in [f.name for f in SentEmail._meta.get_fields()]

    def test_failed_send_is_logged_with_error(self, viewer, rich_bid, monkeypatch):
        def _boom(self, fail_silently=False):
            raise Exception("SMTP said no")

        monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", _boom)
        SentEmail.objects.all().delete()
        send_new_bid_email(viewer, rich_bid)  # must not raise — same external behavior as fail_silently

        entry = SentEmail.objects.get()
        assert entry.success is False
        assert "SMTP said no" in entry.error


@pytest.mark.django_db
class TestSentEmailLogView:
    def test_admin_can_view(self, api_client, admin_user, viewer, rich_bid):
        send_new_bid_email(viewer, rich_bid)
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/notifications/sent-log/")
        assert response.status_code == 200
        assert response.data["count"] >= 1

    def test_viewer_gets_403(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.get("/api/v1/notifications/sent-log/")
        assert response.status_code == 403

    def test_filter_by_success(self, api_client, admin_user, viewer, rich_bid, monkeypatch):
        SentEmail.objects.all().delete()
        send_new_bid_email(viewer, rich_bid)

        def _boom(self, fail_silently=False):
            raise Exception("boom")

        monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", _boom)
        send_new_bid_email(viewer, rich_bid)

        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/notifications/sent-log/", {"success": "false"})
        assert response.data["count"] == 1
        assert response.data["results"][0]["success"] is False

    def test_filter_by_recipient(self, api_client, admin_user, viewer, rich_bid):
        SentEmail.objects.all().delete()
        send_new_bid_email(viewer, rich_bid)
        response_recipient = viewer.email
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.get("/api/v1/notifications/sent-log/", {"recipient": response_recipient})
        assert response.data["count"] == 1
