"""§Phase 20 item 5: welcome email — global switch (default OFF), admin-
triggered send/resend, external-recipient content reduction, and audit."""

import pytest
from django.core import mail

from apps.audit.models import AuditEntry
from apps.bids.models import Bid, BidEngagement, Client, Person
from apps.settings_admin.models import WelcomeEmailSettings
from apps.settings_admin.services import NoEmailError, WelcomeEmailsDisabledError, send_welcome_email

from conftest import login


@pytest.fixture
def client_obj(db):
    return Client.objects.create(name="Welcome Email Co", canonical_name="welcome email co")


@pytest.fixture
def bid(db, client_obj):
    return Bid.objects.create(
        client=client_obj,
        description="a bid",
        submission_date="2026-09-15",
        security_amount_raw="9,00,000",
        bg_bank="AB Bank",
    )


@pytest.fixture
def person_with_email(db):
    return Person.objects.create(canonical_name="Has Email", email="hasemail@example.com")


@pytest.fixture
def engagement(bid, person_with_email):
    return BidEngagement.objects.create(bid=bid, person=person_with_email, days=5, engaged_from="2026-09-01", engaged_to="2026-09-05")


@pytest.mark.django_db
class TestGlobalSwitch:
    def test_defaults_to_disabled(self):
        assert WelcomeEmailSettings.load().enabled is False

    def test_admin_can_toggle_and_it_is_audited(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.patch("/api/v1/settings/welcome-email/", {"enabled": True}, format="json")
        assert response.status_code == 200
        assert response.data["enabled"] is True
        assert WelcomeEmailSettings.load().enabled is True
        assert AuditEntry.objects.filter(action=AuditEntry.Action.WELCOME_EMAIL_SETTINGS).exists()

    def test_editor_gets_403(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.patch("/api/v1/settings/welcome-email/", {"enabled": True}, format="json")
        assert response.status_code == 403

    def test_admin_without_manage_welcome_emails_capability_cannot_toggle(self, api_client, admin_user):
        # Matches every other /settings/ endpoint's convention (e.g.
        # NotificationPolicyViewSet): GET only needs access_master_settings,
        # the specific capability gates writes only.
        from apps.settings_admin.services import grant_capability

        grant_capability(admin_user, "manage_welcome_emails", False, admin_user)
        login(api_client, admin_user, "AdminPass123!")
        assert api_client.get("/api/v1/settings/welcome-email/").status_code == 200
        response = api_client.patch("/api/v1/settings/welcome-email/", {"enabled": True}, format="json")
        assert response.status_code == 403


@pytest.mark.django_db
class TestSendWelcomeEmailService:
    def test_blocked_while_disabled(self, engagement, admin_user):
        with pytest.raises(WelcomeEmailsDisabledError):
            send_welcome_email(engagement, admin_user)
        assert len(mail.outbox) == 0

    def test_blocked_without_email(self, bid, admin_user):
        WelcomeEmailSettings.objects.create(pk=1, enabled=True)
        no_email_person = Person.objects.create(canonical_name="No Email")
        eng = BidEngagement.objects.create(bid=bid, person=no_email_person, days=2)
        with pytest.raises(NoEmailError):
            send_welcome_email(eng, admin_user)

    def test_sends_records_timestamp_and_audits(self, engagement, admin_user):
        WelcomeEmailSettings.objects.create(pk=1, enabled=True)
        mail.outbox = []
        send_welcome_email(engagement, admin_user)

        engagement.refresh_from_db()
        assert engagement.welcome_email_sent_at is not None
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["hasemail@example.com"]

        entry = AuditEntry.objects.get(action=AuditEntry.Action.WELCOME_EMAIL_SENT)
        assert entry.bid_id == engagement.bid_id
        assert "hasemail@example.com" in entry.new_value

    def test_resend_updates_timestamp_and_sends_again(self, engagement, admin_user):
        WelcomeEmailSettings.objects.create(pk=1, enabled=True)
        send_welcome_email(engagement, admin_user)
        first_sent_at = BidEngagement.objects.get(pk=engagement.pk).welcome_email_sent_at

        mail.outbox = []
        send_welcome_email(engagement, admin_user)
        engagement.refresh_from_db()

        assert len(mail.outbox) == 1
        assert engagement.welcome_email_sent_at != first_sent_at
        assert AuditEntry.objects.filter(action=AuditEntry.Action.WELCOME_EMAIL_SENT).count() == 2

    def test_never_sends_without_the_global_switch_regardless_of_who_calls_it(self, engagement, admin_user, editor):
        # The gate is on the service itself, not the view's permission check.
        with pytest.raises(WelcomeEmailsDisabledError):
            send_welcome_email(engagement, editor)


@pytest.mark.django_db
class TestExternalRecipientReduction:
    def test_external_recipient_gets_no_financial_or_bg_details(self, bid, admin_user):
        WelcomeEmailSettings.objects.create(pk=1, enabled=True)
        external_person = Person.objects.create(
            canonical_name="External Person", email="ext@example.com", person_type=Person.PersonType.EXTERNAL
        )
        eng = BidEngagement.objects.create(bid=bid, person=external_person, days=3)

        mail.outbox = []
        send_welcome_email(eng, admin_user)

        sent = mail.outbox[0]
        assert "9,00,000" not in sent.body
        assert "AB Bank" not in sent.body
        for alt_body, _mimetype in sent.alternatives:
            assert "9,00,000" not in alt_body
            assert "AB Bank" not in alt_body

    def test_internal_recipient_gets_financial_and_bg_details(self, engagement, admin_user):
        WelcomeEmailSettings.objects.create(pk=1, enabled=True)
        mail.outbox = []
        send_welcome_email(engagement, admin_user)

        sent = mail.outbox[0]
        assert "9,00,000" in sent.body
        assert "AB Bank" in sent.body

    def test_content_includes_greeting_reference_dates_and_contact(self, bid, admin_user):
        WelcomeEmailSettings.objects.create(pk=1, enabled=True)
        bid.bid_manager = Person.objects.create(canonical_name="Manager Contact", email="mgr@example.com")
        bid.save(update_fields=["bid_manager"])
        person = Person.objects.create(canonical_name="Greeting Test", email="greet@example.com")
        eng = BidEngagement.objects.create(bid=bid, person=person, days=4, engaged_from="2026-09-01", engaged_to="2026-09-05")

        mail.outbox = []
        send_welcome_email(eng, admin_user)

        body = mail.outbox[0].body
        assert "Greeting Test" in body
        assert bid.reference in body
        assert "2026-09-01" in body
        assert "Manager Contact" in body


@pytest.mark.django_db
class TestSendWelcomeEmailApiView:
    def test_disabled_by_default_returns_400(self, api_client, admin_user, engagement):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post(f"/api/v1/settings/engagements/{engagement.id}/welcome-email/")
        assert response.status_code == 400

    def test_admin_can_send_once_enabled(self, api_client, admin_user, engagement):
        WelcomeEmailSettings.objects.create(pk=1, enabled=True)
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post(f"/api/v1/settings/engagements/{engagement.id}/welcome-email/")
        assert response.status_code == 200
        assert response.data["welcome_email_sent_at"] is not None

    def test_editor_gets_403(self, api_client, editor, engagement):
        WelcomeEmailSettings.objects.create(pk=1, enabled=True)
        login(api_client, editor, "EditorPass123!")
        response = api_client.post(f"/api/v1/settings/engagements/{engagement.id}/welcome-email/")
        assert response.status_code == 403
