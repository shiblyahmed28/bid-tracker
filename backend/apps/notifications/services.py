"""Where every notification actually gets created (§16). Bid.apply_change()
calls notify_field_change() for manual and sync-driven edits alike; bid
creation (app or sheet) calls notify_new_bid(); the daily Beat task calls
notify_deadline(); send_pending_digests() is the batching boundary (§9 step 7)."""

from .emails import send_deadline_email, send_digest_email, send_new_bid_email
from .models import (
    DEFAULT_ON_FIELDS,
    Notification,
    NotificationSubscription,
    PendingDigestItem,
    notification_key_for,
)


def _subscribed_user_ids(field_key):
    from apps.accounts.models import User

    default_on = field_key in DEFAULT_ON_FIELDS
    active_ids = set(
        User.objects.filter(is_active=True, notifications_muted=False).values_list("id", flat=True)
    )
    overrides = dict(
        NotificationSubscription.objects.filter(field_name=field_key).values_list("user_id", "enabled")
    )
    return {uid for uid in active_ids if overrides.get(uid, default_on)}


def notify_field_change(bid, raw_field_name, old_value, new_value, actor):
    from apps.accounts.models import User
    from apps.notifications.models import NOTIFICATION_FIELDS

    key = notification_key_for(raw_field_name)
    if key is None:
        return

    user_ids = _subscribed_user_ids(key)
    if actor is not None:
        user_ids.discard(actor.id)
    if not user_ids:
        return

    label = dict(NOTIFICATION_FIELDS).get(key, key)
    users = list(User.objects.filter(id__in=user_ids))

    Notification.objects.bulk_create(
        [
            Notification(
                user=u,
                kind=Notification.Kind.FIELD_CHANGE,
                title=f"{bid.client.name} — {label}: {new_value or '—'}",
                body=f"{bid.reference}: {old_value or '—'} → {new_value or '—'}",
                bid=bid,
            )
            for u in users
        ]
    )
    PendingDigestItem.objects.bulk_create(
        [
            PendingDigestItem(user=u, bid=bid, field_name=key, old_value=old_value, new_value=new_value)
            for u in users
            if u.email_digest
        ]
    )


def notify_new_bid(bid):
    """One notification regardless of column subscriptions — viewers get
    these too (§16). email_newbid gates the immediate email only."""
    from apps.accounts.models import User

    recipients = list(User.objects.filter(is_active=True, notifications_muted=False))
    if not recipients:
        return

    title = f"{bid.client.name} — {(bid.description or '')[:60]} · due {bid.submission_date or 'unknown'}"
    Notification.objects.bulk_create(
        [Notification(user=u, kind=Notification.Kind.NEW_BID, title=title, bid=bid) for u in recipients]
    )
    for u in recipients:
        if u.email_newbid:
            send_new_bid_email(u, bid)


def notify_deadline(bid):
    """7 days before submission_date, sent immediately, own toggle (§16).
    Caller is responsible for deduplication (Bid.deadline_alert_sent_at)."""
    from apps.accounts.models import User

    recipients = list(
        User.objects.filter(is_active=True, notifications_muted=False, email_deadline=True)
    )
    if not recipients:
        return

    title = f"{bid.client.name} — submission due in 7 days ({bid.submission_date})"
    Notification.objects.bulk_create(
        [Notification(user=u, kind=Notification.Kind.DEADLINE, title=title, bid=bid) for u in recipients]
    )
    for u in recipients:
        send_deadline_email(u, bid)


def send_pending_digests():
    """Batches every queued PendingDigestItem into one email per user (§9
    step 7, §16) — called once at the end of every sync run, scheduled or
    manual, so a 40-bid sync sends one email per user, not forty."""
    from apps.accounts.models import User

    user_ids = PendingDigestItem.objects.values_list("user_id", flat=True).distinct()
    sent = 0
    for user in User.objects.filter(id__in=user_ids):
        items = list(
            PendingDigestItem.objects.filter(user=user).select_related("bid", "bid__client")
        )
        if not items:
            continue
        send_digest_email(user, items)
        PendingDigestItem.objects.filter(user=user).delete()
        sent += 1
    return sent
