"""Seeds the 8 managed dropdowns and backfills ChoiceValue from every
distinct value already sitting in the bids table, so nothing currently in
the database disappears from a dropdown (Phase 15A) — plus seeds the
notification-policy and deadline-reminder-rule defaults (Phase 15C).

Kept self-contained (constants inlined here, not imported from services.py)
since a migration is a frozen snapshot — it must not depend on application
code that could change out from under it later.
"""

from django.db import migrations

# ChoiceList key -> (label, Bid field name or None for the structural delivery_type case)
CHOICE_LISTS = [
    ("stage", "Stage", "stage"),
    ("security_mode", "Security mode", "security_mode"),
    ("initiation_mode", "Initiation mode", "initiation_mode"),
    ("procurement_type", "Procurement type", "procurement_type"),
    ("issuing_bank", "Issuing bank", "bg_bank"),
    ("submission_status", "Submission status", "submission_status"),
    ("result", "Result", "result"),
    ("delivery_type", "Delivery type", None),
]

DELIVERY_TYPE_VALUES = [("goods", "Goods"), ("works", "Works"), ("service", "Service")]

NOTIFICATION_POLICIES = [
    ("result_won", "Bid result: Won", True, True, ["editor", "viewer"]),
    ("result_lost", "Bid result: Lost", True, True, ["editor", "viewer"]),
    ("result_not_submitted", "Submission status: Not Submitted", True, True, ["editor", "viewer"]),
    ("bid_created", "New bid created", True, False, ["admin", "editor", "viewer"]),
    ("field_changed", "Followed field changed", True, False, ["admin", "editor", "viewer"]),
    ("deadline_reminder", "Deadline reminder", True, True, ["admin", "editor", "viewer"]),
]

DEADLINE_RULES = [(7, True), (14, False), (21, False)]


def seed(apps, schema_editor):
    ChoiceList = apps.get_model("settings_admin", "ChoiceList")
    ChoiceValue = apps.get_model("settings_admin", "ChoiceValue")
    NotificationPolicy = apps.get_model("settings_admin", "NotificationPolicy")
    DeadlineReminderRule = apps.get_model("settings_admin", "DeadlineReminderRule")
    Bid = apps.get_model("bids", "Bid")

    for key, label, field_name in CHOICE_LISTS:
        choice_list, _ = ChoiceList.objects.get_or_create(
            key=key, defaults={"label": label, "is_locked": True}
        )

        if field_name is None:
            # delivery_type: three fixed, structural values — not derived
            # from any single free-text column (see apps/bids/models.py's
            # is_goods/is_works/is_service booleans).
            for order, (value, value_label) in enumerate(DELIVERY_TYPE_VALUES):
                ChoiceValue.objects.get_or_create(
                    list=choice_list,
                    value=value,
                    defaults={"label": value_label, "sort_order": order, "is_active": True},
                )
            continue

        distinct_values = (
            Bid.objects.exclude(**{field_name: ""})
            .exclude(**{f"{field_name}__isnull": True})
            .values_list(field_name, flat=True)
            .distinct()
        )
        for order, value in enumerate(sorted(v for v in distinct_values if v)):
            ChoiceValue.objects.get_or_create(
                list=choice_list, value=value, defaults={"label": value, "sort_order": order, "is_active": True}
            )

    for event_key, label, default_in_app, default_email, roles in NOTIFICATION_POLICIES:
        NotificationPolicy.objects.get_or_create(
            event_key=event_key,
            defaults={
                "label": label,
                "default_in_app": default_in_app,
                "default_email": default_email,
                "applies_to_roles": roles,
                "is_active": True,
            },
        )

    for days_before, is_active in DEADLINE_RULES:
        DeadlineReminderRule.objects.get_or_create(
            days_before=days_before,
            defaults={"is_active": is_active, "applies_to_roles": ["admin", "editor", "viewer"]},
        )


def unseed(apps, schema_editor):
    ChoiceList = apps.get_model("settings_admin", "ChoiceList")
    NotificationPolicy = apps.get_model("settings_admin", "NotificationPolicy")
    DeadlineReminderRule = apps.get_model("settings_admin", "DeadlineReminderRule")
    ChoiceList.objects.filter(key__in=[k for k, _, _ in CHOICE_LISTS]).delete()
    NotificationPolicy.objects.filter(event_key__in=[k for k, *_ in NOTIFICATION_POLICIES]).delete()
    DeadlineReminderRule.objects.filter(days_before__in=[d for d, _ in DEADLINE_RULES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("settings_admin", "0001_initial"),
        ("bids", "0004_bid_deadline_alert_sent_at"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
