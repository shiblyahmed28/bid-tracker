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
    for `delivery_type`, which has no backing free-text column to update.

    If `new_value` collides with another ChoiceValue already in this list —
    exactly the real-world case this feature exists for, e.g. merging
    "AB Bank Ltd." into an existing "AB Bank Limited" — this merges into
    that existing row and removes the now-redundant one, rather than
    tripping the (list, value) uniqueness constraint. Returns
    (updated_bid_count, the surviving ChoiceValue)."""
    from apps.bids.models import Bid

    field_name = CHOICE_LIST_FIELD_MAP.get(choice_value.list.key)
    old_value = choice_value.value

    with transaction.atomic():
        updated_count = 0
        if field_name:
            updated_count = Bid.all_objects.filter(**{field_name: old_value}).update(**{field_name: new_value})

        merge_target = (
            ChoiceValue.objects.filter(list=choice_value.list, value=new_value)
            .exclude(pk=choice_value.pk)
            .first()
        )
        if merge_target:
            merge_target.label = new_label
            merge_target.save(update_fields=["label"])
            choice_value.delete()
            result_value = merge_target
        else:
            choice_value.value = new_value
            choice_value.label = new_label
            choice_value.save(update_fields=["value", "label"])
            result_value = choice_value

        AuditEntry.objects.create(
            actor=actor,
            actor_label=actor.email,
            action=AuditEntry.Action.CHOICE_VALUE_RENAME,
            field=choice_value.list.key,
            old_value=old_value,
            new_value=new_value,
        )

    return updated_count, result_value


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


def clear_capability_override(target_user, capability, actor):
    """Reverts one capability to its role default (the third state of the
    Phase 16 capability matrix's inherited/granted/revoked cycle). Guarded
    the same way as grant_capability: if clearing would leave the *actor's
    own* manage_users/access_master_settings effectively off (i.e. their
    role default for it is False), block it — clearing is just as much a
    self-lockout risk as an explicit revoke when the role default is off."""
    from .capabilities import role_default_capabilities

    would_be_granted = capability in role_default_capabilities(target_user.role)
    if (
        target_user.id == actor.id
        and capability in SELF_LOCKOUT_PROTECTED_CAPABILITIES
        and not would_be_granted
    ):
        raise SelfLockoutError(f"You cannot revoke {capability} from yourself.")

    with transaction.atomic():
        deleted, _ = UserCapability.objects.filter(user=target_user, capability=capability).delete()
        if deleted:
            AuditEntry.objects.create(
                actor=actor,
                actor_label=actor.email,
                action=AuditEntry.Action.CAPABILITY_GRANT
                if would_be_granted
                else AuditEntry.Action.CAPABILITY_REVOKE,
                field=capability,
                new_value=f"{target_user.email} — reverted to role default by {actor.email}",
            )
    return bool(deleted)


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


# ---------- Engaged resources: dedup/merge, engagement history, welcome email (§Phase 20) ----------


class NoEmailError(Exception):
    pass


class WelcomeEmailsDisabledError(Exception):
    pass


def _normalized_name_key(name):
    import re

    return re.sub(r"\s+", " ", name.strip()).casefold()


def find_duplicate_person_groups():
    """Groups Person rows whose canonical_name is the same once whitespace-
    collapsed and case-folded — the "Aminul Quader Khalili " vs "Aminul
    Quader Khalili" case (§Phase 20 item 3). canonical_name is unique at the
    DB level but only case-sensitively, so historical rows created before
    today's case-insensitive create/sync guards can still collide this way."""
    from collections import defaultdict

    from apps.bids.models import Person

    groups = defaultdict(list)
    for person in Person.objects.all():
        groups[_normalized_name_key(person.canonical_name)].append(person)

    return [people for people in groups.values() if len(people) > 1]


class SamePersonError(Exception):
    pass


def merge_persons(survivor, duplicate, actor):
    """Merges `duplicate` into `survivor` (§Phase 20 item 3): every
    BidEngagement, and every cam/sales_resource/bid_manager reference,
    moves to the survivor. A duplicate's engagement on a bid the survivor is
    *already* engaged on can't be reassigned (unique_together) — that row is
    dropped rather than merged, keeping the survivor's own data as canonical.

    `duplicate` is never hard-deleted — it's a soft historical record now
    (is_active=False), avoiding a PROTECT failure and keeping the audit
    trail's actor references intact. One consolidated AuditEntry describes
    the whole merge rather than one per reassigned bid."""
    from django.db import transaction

    from apps.bids.models import Bid, BidEngagement

    if survivor.pk == duplicate.pk:
        raise SamePersonError("Cannot merge a person into themselves.")

    with transaction.atomic():
        existing_bid_ids = set(
            BidEngagement.objects.filter(person=survivor).values_list("bid_id", flat=True)
        )
        dup_engagements = BidEngagement.objects.filter(person=duplicate)
        skipped = dup_engagements.filter(bid_id__in=existing_bid_ids).count()
        dup_engagements.filter(bid_id__in=existing_bid_ids).delete()
        reassigned_engagements = dup_engagements.exclude(bid_id__in=existing_bid_ids).update(person=survivor)

        reassigned_cam = Bid.all_objects.filter(cam=duplicate).update(cam=survivor)
        reassigned_sales = Bid.all_objects.filter(sales_resource=duplicate).update(sales_resource=survivor)
        reassigned_manager = Bid.all_objects.filter(bid_manager=duplicate).update(bid_manager=survivor)

        combined_aliases = list(dict.fromkeys([*survivor.aliases, *duplicate.aliases, duplicate.canonical_name]))
        survivor.aliases = combined_aliases
        survivor.save(update_fields=["aliases"])

        duplicate.is_active = False
        duplicate.save(update_fields=["is_active"])

        summary = (
            f"engagements: {reassigned_engagements} moved, {skipped} skipped (already on that bid); "
            f"cam: {reassigned_cam}; sales_resource: {reassigned_sales}; bid_manager: {reassigned_manager}"
        )
        AuditEntry.objects.create(
            actor=actor,
            actor_label=actor.email,
            action=AuditEntry.Action.PERSON_MERGE,
            old_value=duplicate.canonical_name,
            new_value=f"{survivor.canonical_name} ({summary})",
        )

    return {
        "engagements_reassigned": reassigned_engagements,
        "engagements_skipped": skipped,
        "cam_reassigned": reassigned_cam,
        "sales_resource_reassigned": reassigned_sales,
        "bid_manager_reassigned": reassigned_manager,
    }


def send_welcome_email(engagement, actor):
    """Admin-triggered only (§Phase 20 item 5) — never called automatically
    from the bid create/edit flow. Blocked entirely while the global switch
    is off, regardless of who clicks the button. A resend is just another
    call to this same function — there's no hard one-send limit, only the
    UI's "Send" vs "Resend" label tells the two apart."""
    from django.utils import timezone

    from apps.notifications.emails import send_welcome_engagement_email

    from .models import WelcomeEmailSettings

    if not WelcomeEmailSettings.load().enabled:
        raise WelcomeEmailsDisabledError("Welcome emails are turned off. An admin must enable them first.")
    if not engagement.person.email:
        raise NoEmailError(f"{engagement.person.canonical_name} has no email address on file.")

    send_welcome_engagement_email(engagement)

    engagement.welcome_email_sent_at = timezone.now()
    engagement.save(update_fields=["welcome_email_sent_at"])

    AuditEntry.objects.create(
        actor=actor,
        actor_label=actor.email,
        action=AuditEntry.Action.WELCOME_EMAIL_SENT,
        bid=engagement.bid,
        field="welcome_email",
        new_value=f"{engagement.person.canonical_name} <{engagement.person.email}>",
    )
    return engagement
