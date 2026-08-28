import pytest
from django.core import mail

from apps.bids.models import Bid, Client
from apps.notifications.models import Notification
from apps.settings_admin.models import DeadlineReminderRule, DeadlineReminderSent, NotificationPolicy
from apps.settings_admin.services import notify_policy_transition, send_deadline_reminders

from conftest import login


@pytest.fixture
def bid(db):
    client_obj = Client.objects.create(name="Policy Test Co", canonical_name="policy test co")
    return Bid.objects.create(
        client=client_obj, description="test", submission_date="2026-09-10", result="PENDING"
    )


@pytest.mark.django_db
def test_result_won_transition_notifies_editors_and_viewers_in_app_and_email(viewer, editor, admin_user, bid):
    mail.outbox = []
    notify_policy_transition(bid, "result", "PENDING", "WON")

    assert Notification.objects.filter(user=viewer).exists()
    assert Notification.objects.filter(user=editor).exists()
    assert not Notification.objects.filter(user=admin_user).exists()  # policy applies_to_roles excludes admin
    assert len(mail.outbox) == 2  # viewer + editor


@pytest.mark.django_db
def test_result_lost_transition_fires_policy(viewer, bid):
    notify_policy_transition(bid, "result", "PENDING", "LOST")
    assert Notification.objects.filter(user=viewer, title__icontains="Lost").exists()


@pytest.mark.django_db
def test_submission_status_not_submitted_transition_fires_policy(viewer, bid):
    notify_policy_transition(bid, "submission_status", "SUBMITTED", "NOT SUBMITTED")
    assert Notification.objects.filter(user=viewer).exists()


@pytest.mark.django_db
def test_no_transition_fires_nothing(viewer, bid):
    notify_policy_transition(bid, "remarks", "old", "new")
    notify_policy_transition(bid, "result", "PENDING", "QUALIFIED")  # not Won/Lost
    assert not Notification.objects.filter(user=viewer).exists()


@pytest.mark.django_db
def test_re_transition_to_same_value_does_not_refire(viewer, bid):
    notify_policy_transition(bid, "result", "WON", "WON")
    assert not Notification.objects.filter(user=viewer).exists()


@pytest.mark.django_db
def test_user_override_wins_over_policy_default(viewer, bid):
    from apps.settings_admin.models import UserNotificationPolicyOverride

    policy = NotificationPolicy.objects.get(event_key="result_won")
    UserNotificationPolicyOverride.objects.create(user=viewer, policy=policy, in_app=False, email=False)

    mail.outbox = []
    notify_policy_transition(bid, "result", "PENDING", "WON")

    assert not Notification.objects.filter(user=viewer).exists()
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_inactive_policy_does_not_fire(viewer, bid):
    NotificationPolicy.objects.filter(event_key="result_won").update(is_active=False)
    notify_policy_transition(bid, "result", "PENDING", "WON")
    assert not Notification.objects.filter(user=viewer).exists()


@pytest.mark.django_db
def test_deadline_rules_seeded_only_7_days_active():
    rules = {r.days_before: r.is_active for r in DeadlineReminderRule.objects.all()}
    assert rules == {7: True, 14: False, 21: False}


@pytest.mark.django_db
def test_send_deadline_reminders_dedupes_per_bid_per_rule(viewer, bid):
    import datetime

    from django.utils import timezone

    bid.submission_date = timezone.localdate() + datetime.timedelta(days=7)
    bid.save(update_fields=["submission_date"])

    mail.outbox = []
    first_sent = send_deadline_reminders()
    second_sent = send_deadline_reminders()

    assert first_sent == 1
    assert second_sent == 0  # already sent for the 7-day rule on this bid
    assert DeadlineReminderSent.objects.filter(bid=bid).count() == 1


@pytest.mark.django_db
def test_activating_the_14_day_rule_sends_a_second_independent_reminder(viewer, bid):
    import datetime

    from django.utils import timezone

    DeadlineReminderRule.objects.filter(days_before=14).update(is_active=True)
    bid.submission_date = timezone.localdate() + datetime.timedelta(days=14)
    bid.save(update_fields=["submission_date"])

    sent = send_deadline_reminders()
    assert sent == 1
    rule_14 = DeadlineReminderRule.objects.get(days_before=14)
    assert DeadlineReminderSent.objects.filter(bid=bid, rule=rule_14).exists()


@pytest.mark.django_db
def test_notification_policy_update_via_api_requires_manage_notification_policy(api_client, admin_user):
    login(api_client, admin_user, "AdminPass123!")
    policy = NotificationPolicy.objects.get(event_key="result_won")
    response = api_client.patch(
        f"/api/v1/settings/notification-policies/{policy.id}/", {"default_email": False}, format="json"
    )
    assert response.status_code == 200
    policy.refresh_from_db()
    assert policy.default_email is False
