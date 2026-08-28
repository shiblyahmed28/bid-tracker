import pytest
from django.core import mail

from apps.bids.models import Bid, Client
from apps.notifications.models import Notification, NotificationSubscription, PendingDigestItem
from apps.notifications.services import notify_deadline, notify_field_change, notify_new_bid, send_pending_digests

from conftest import login


@pytest.fixture
def bid(db):
    client_obj = Client.objects.create(name="Acme Corp", canonical_name="acme corp")
    return Bid.objects.create(client=client_obj, description="Test bid", submission_date="2026-09-10")


@pytest.mark.django_db
def test_default_on_field_notifies_without_explicit_subscription(viewer, bid):
    notify_field_change(bid, "result", "Pending", "Won", actor=None)
    assert Notification.objects.filter(user=viewer, kind=Notification.Kind.FIELD_CHANGE).exists()
    assert PendingDigestItem.objects.filter(user=viewer, field_name="result").exists()


@pytest.mark.django_db
def test_default_off_field_does_not_notify_without_override(viewer, bid):
    notify_field_change(bid, "remarks", "old", "new", actor=None)
    assert not Notification.objects.filter(user=viewer).exists()


@pytest.mark.django_db
def test_explicit_override_can_disable_a_default_on_field(viewer, bid):
    NotificationSubscription.objects.create(user=viewer, field_name="result", enabled=False)
    notify_field_change(bid, "result", "Pending", "Won", actor=None)
    assert not Notification.objects.filter(user=viewer).exists()


@pytest.mark.django_db
def test_explicit_override_can_enable_a_default_off_field(viewer, bid):
    NotificationSubscription.objects.create(user=viewer, field_name="tender_id", enabled=True)
    notify_field_change(bid, "tender_id", "OLD-1", "NEW-1", actor=None)
    assert Notification.objects.filter(user=viewer).exists()


@pytest.mark.django_db
def test_raw_money_fields_collapse_onto_one_notification_key(viewer, bid):
    notify_field_change(bid, "security_amount_raw", "1,000", "2,000", actor=None)
    notify_field_change(bid, "security_currency", "BDT", "USD", actor=None)
    items = PendingDigestItem.objects.filter(user=viewer)
    assert items.count() == 2
    assert all(item.field_name == "security_amount" for item in items)


@pytest.mark.django_db
def test_actor_is_excluded_from_their_own_change_notification(editor, bid):
    notify_field_change(bid, "result", "Pending", "Won", actor=editor)
    assert not Notification.objects.filter(user=editor).exists()


@pytest.mark.django_db
def test_muted_user_gets_no_notification(viewer, bid):
    viewer.notifications_muted = True
    viewer.save(update_fields=["notifications_muted"])
    notify_field_change(bid, "result", "Pending", "Won", actor=None)
    assert not Notification.objects.filter(user=viewer).exists()


@pytest.mark.django_db
def test_new_bid_notifies_everyone_regardless_of_subscriptions(viewer, editor, bid):
    NotificationSubscription.objects.create(user=viewer, field_name="result", enabled=False)
    notify_new_bid(bid)
    assert Notification.objects.filter(user=viewer, kind=Notification.Kind.NEW_BID).exists()
    assert Notification.objects.filter(user=editor, kind=Notification.Kind.NEW_BID).exists()


@pytest.mark.django_db
def test_new_bid_email_respects_per_user_toggle(viewer, bid):
    viewer.email_newbid = False
    viewer.save(update_fields=["email_newbid"])
    mail.outbox = []
    notify_new_bid(bid)
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_deadline_alert_respects_toggle_and_sends_email(viewer, bid):
    mail.outbox = []
    notify_deadline(bid)
    assert Notification.objects.filter(user=viewer, kind=Notification.Kind.DEADLINE).exists()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_digest_batches_multiple_changes_into_one_email_per_user(viewer, editor, bid):
    notify_field_change(bid, "result", "Pending", "Won", actor=None)
    notify_field_change(bid, "submission_status", "Not Submitted", "Submitted", actor=None)
    mail.outbox = []
    sent = send_pending_digests()
    assert sent == 2  # viewer + editor, one email each
    assert len(mail.outbox) == 2
    assert PendingDigestItem.objects.count() == 0


@pytest.mark.django_db
def test_digest_sends_nothing_when_queue_is_empty():
    mail.outbox = []
    assert send_pending_digests() == 0
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_forty_bid_changes_send_one_email_per_user_not_forty(viewer, editor):
    """The explicit Phase 13 acceptance criterion: a sync touching 40 bids
    across N users must send one email per user, not one per change."""
    client_obj = Client.objects.create(name="Bulk Sync Co", canonical_name="bulk sync co")
    bids = [
        Bid.objects.create(client=client_obj, description=f"Bid {i}", submission_date="2026-09-10")
        for i in range(40)
    ]
    for bid in bids:
        notify_field_change(bid, "result", "PENDING", "WON", actor=None)

    mail.outbox = []
    sent = send_pending_digests()
    assert sent == 2  # viewer + editor
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_settings_get_returns_defaults_and_patch_persists_overrides(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.get("/api/v1/notifications/settings/")
    assert response.status_code == 200
    assert response.data["fields"]["result"] is True
    assert response.data["fields"]["tender_id"] is False

    patch = api_client.patch(
        "/api/v1/notifications/settings/",
        {"notifications_muted": True, "fields": {"tender_id": True}},
        format="json",
    )
    assert patch.status_code == 200
    assert patch.data["notifications_muted"] is True
    assert patch.data["fields"]["tender_id"] is True

    viewer.refresh_from_db()
    assert viewer.notifications_muted is True
    assert NotificationSubscription.objects.get(user=viewer, field_name="tender_id").enabled is True


@pytest.mark.django_db
def test_settings_patch_rejects_unknown_field_key(api_client, viewer):
    login(api_client, viewer, "ViewerPass123!")
    response = api_client.patch(
        "/api/v1/notifications/settings/", {"fields": {"not_a_real_field": True}}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_mark_read_and_mark_all_read(api_client, viewer, bid):
    Notification.objects.create(user=viewer, kind=Notification.Kind.NEW_BID, title="A", bid=bid)
    n2 = Notification.objects.create(user=viewer, kind=Notification.Kind.NEW_BID, title="B", bid=bid)

    login(api_client, viewer, "ViewerPass123!")
    r1 = api_client.post(f"/api/v1/notifications/{n2.id}/read/")
    assert r1.status_code == 204
    n2.refresh_from_db()
    assert n2.read is True

    r2 = api_client.post("/api/v1/notifications/mark-all-read/")
    assert r2.status_code == 200
    assert r2.data["updated"] == 1
    assert Notification.objects.filter(user=viewer, read=False).count() == 0


@pytest.mark.django_db
def test_list_notifications_is_scoped_to_own_user(api_client, viewer, editor, bid):
    Notification.objects.create(user=viewer, kind=Notification.Kind.NEW_BID, title="mine", bid=bid)
    Notification.objects.create(user=editor, kind=Notification.Kind.NEW_BID, title="not mine", bid=bid)

    login(api_client, viewer, "ViewerPass123!")
    response = api_client.get("/api/v1/notifications/")
    rows = response.data["results"] if isinstance(response.data, dict) else response.data
    assert len(rows) == 1
    assert rows[0]["title"] == "mine"
