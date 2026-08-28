"""Phase 15's mutating logic — kept out of views.py so it's independently
testable and reusable from the sync pipeline (apps/sync/sync.py) without
either module importing the other's request/response plumbing."""

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEntry

from .capabilities import SELF_LOCKOUT_PROTECTED_CAPABILITIES
from .models import ChoiceValue, DeadlineReminderRule, UserCapability

# ChoiceList.key -> Bid field name. None means "structural" (delivery_type) —
# there is no single free-text column to rename/reconcile against.
CHOICE_LIST_FIELD_MAP = {
    "stage": "stage",
    "security_mode": "security_mode",
    "initiation_mode": "initiation_mode",
    "procurement_type": "procurement_type",
    "issuing_bank": "bg_bank",
    "submission_status": "submission_status",
    "result": "result",
    "delivery_type": None,
}


class LastAdminError(Exception):
    pass


class SelfLockoutError(Exception):
    pass


def rename_value(choice_value, new_value, new_label, actor):
    """Renames a ChoiceValue and every Bid row currently using the old value,
    in one transaction, with an audit entry (§Phase 15A). A no-op on Bid rows
    for `delivery_type`, which has no backing free-text column to update."""
    from apps.bids.models import Bid

    field_name = CHOICE_LIST_FIELD_MAP.get(choice_value.list.key)
    old_value = choice_value.value

    with transaction.atomic():
        updated_count = 0
        if field_name:
            updated_count = Bid.all_objects.filter(**{field_name: old_value}).update(**{field_name: new_value})

        choice_value.value = new_value
        choice_value.label = new_label
        choice_value.save(update_fields=["value", "label"])

        AuditEntry.objects.create(
            actor=actor,
            actor_label=actor.email,
            action=AuditEntry.Action.CHOICE_VALUE_RENAME,
            field=choice_value.list.key,
            old_value=old_value,
            new_value=new_value,
        )

    return updated_count


def sync_choice_values_from_bids():
    """Reconciles ChoiceValue against whatever is actually in the bids table
    right now — called once at the end of every sync run (scheduled or
    manual). Purely additive: never removes or deactivates a value, only
    auto-creates ones the sync introduced, flagged created_by_sync=True for
    admin review (§Phase 15A). Does not touch delivery_type (structural, not
    sheet-driven text)."""
    from apps.bids.models import Bid

    from .models import ChoiceList

    created = []
    for list_key, field_name in CHOICE_LIST_FIELD_MAP.items():
        if field_name is None:
            continue
        try:
            choice_list = ChoiceList.objects.get(key=list_key)
        except ChoiceList.DoesNotExist:
            continue

        existing = set(choice_list.values.values_list("value", flat=True))
        distinct_values = (
            Bid.objects.exclude(**{field_name: ""})
            .exclude(**{f"{field_name}__isnull": True})
            .values_list(field_name, flat=True)
            .distinct()
        )
        max_sort = choice_list.values.count()
        for value in distinct_values:
            if value in existing:
                continue
            ChoiceValue.objects.create(
                list=choice_list,
                value=value,
                label=value,
                sort_order=max_sort,
                is_active=True,
                created_by_sync=True,
            )
            existing.add(value)
            max_sort += 1
            created.append((list_key, value))

    return created


def grant_capability(target_user, capability, granted, actor):
    """Sets an explicit UserCapability override, guarding against an admin
    locking themselves out (§Phase 15B). Writes an audit entry naming both
    the actor and the target."""
    if target_user.id == actor.id and capability in SELF_LOCKOUT_PROTECTED_CAPABILITIES and not granted:
        raise SelfLockoutError(f"You cannot revoke {capability} from yourself.")

    with transaction.atomic():
        override, _ = UserCapability.objects.update_or_create(
            user=target_user,
            capability=capability,
            defaults={"granted": granted, "granted_by": actor, "granted_at": timezone.now()},
        )
        AuditEntry.objects.create(
            actor=actor,
            actor_label=actor.email,
            action=AuditEntry.Action.CAPABILITY_GRANT if granted else AuditEntry.Action.CAPABILITY_REVOKE,
            field=capability,
            new_value=f"{target_user.email} — {'granted' if granted else 'revoked'} by {actor.email}",
        )
    return override


def guard_last_admin_demotion(instance, new_role):
    """The last remaining admin can't be demoted — regardless of who's
    changing it (§Phase 15B). Distinct from the pre-existing "you can't
    change your own role at all" rule in UserViewSet."""
    from apps.accounts.models import User

    if instance.role != User.Role.ADMIN or new_role == User.Role.ADMIN:
        return
    remaining_admins = User.objects.filter(role=User.Role.ADMIN, is_active=True).exclude(pk=instance.pk).count()
    if remaining_admins == 0:
        raise LastAdminError("Cannot demote the last remaining admin.")


def notify_policy_transition(bid, field, old_value, new_value):
    """The Phase 15C requirement: result becoming Won/Lost, or submission
    status becoming Not Submitted, notifies every user the matching policy
    applies to — in-app and email, per that policy's (or the user's own
    override's) settings. Runs alongside, not instead of, Phase 13's
    per-column subscription notifications — a policy event and a followed-
    field change are different concepts and may both fire for the same edit."""
    from apps.accounts.models import User
    from apps.notifications.emails import send_policy_event_email
    from apps.notifications.models import Notification

    from .models import NotificationPolicy, UserNotificationPolicyOverride

    event_key = None
    if field == "result" and new_value == "WON" and old_value != "WON":
        event_key = "result_won"
    elif field == "result" and new_value == "LOST" and old_value != "LOST":
        event_key = "result_lost"
    elif field == "submission_status" and new_value == "NOT SUBMITTED" and old_value != "NOT SUBMITTED":
        event_key = "result_not_submitted"
    if event_key is None:
        return

    policy = NotificationPolicy.objects.filter(event_key=event_key, is_active=True).first()
    if policy is None:
        return

    recipients = User.objects.filter(is_active=True, notifications_muted=False, role__in=policy.applies_to_roles)
    overrides = {
        o.user_id: o
        for o in UserNotificationPolicyOverride.objects.filter(policy=policy, user__in=recipients)
    }

    for user in recipients:
        override = overrides.get(user.id)
        in_app = override.in_app if override and override.in_app is not None else policy.default_in_app
        email = override.email if override and override.email is not None else policy.default_email

        if in_app:
            Notification.objects.create(
                user=user,
                kind=Notification.Kind.FIELD_CHANGE,
                title=f"{policy.label} — {bid.client.name}",
                body=f"{bid.reference}: {old_value or '—'} → {new_value or '—'}",
                bid=bid,
            )
        if email:
            send_policy_event_email(user, bid, policy)


def send_deadline_reminders():
    """Loops every active DeadlineReminderRule, deduplicating per bid per
    rule via DeadlineReminderSent — replaces the old hard-coded 7-day-only
    task (§Phase 15C)."""
    import datetime

    from apps.accounts.models import User
    from apps.bids.models import Bid
    from apps.notifications.services import notify_deadline

    from .models import DeadlineReminderSent

    today = timezone.localdate()
    sent_count = 0

    for rule in DeadlineReminderRule.objects.filter(is_active=True):
        target_date = today + datetime.timedelta(days=rule.days_before)
        bids = Bid.objects.filter(submission_date=target_date)

        for bid in bids:
            if DeadlineReminderSent.objects.filter(bid=bid, rule=rule).exists():
                continue

            recipients = set(
                User.objects.filter(
                    is_active=True, notifications_muted=False, role__in=rule.applies_to_roles
                )
            )
            recipients |= set(rule.users.filter(is_active=True, notifications_muted=False))

            for user in recipients:
                if user.email_deadline:
                    notify_deadline_for_rule(bid, user, rule)

            DeadlineReminderSent.objects.create(bid=bid, rule=rule)
            sent_count += 1

    return sent_count


def notify_deadline_for_rule(bid, user, rule):
    from apps.notifications.emails import send_deadline_email
    from apps.notifications.models import Notification

    title = f"{bid.client.name} — submission due in {rule.days_before} days ({bid.submission_date})"
    Notification.objects.create(user=user, kind=Notification.Kind.DEADLINE, title=title, bid=bid)
    send_deadline_email(user, bid, days_before=rule.days_before)
