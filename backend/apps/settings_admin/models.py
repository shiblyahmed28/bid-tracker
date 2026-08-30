from django.conf import settings
from django.db import models


class ChoiceList(models.Model):
    """One row per managed dropdown (Phase 15A). `is_locked` means the *key*
    (and therefore which Bid field/logic it backs) can't be renamed or
    deleted — it says nothing about whether its values can be edited."""

    key = models.SlugField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_locked = models.BooleanField(default=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label


class ChoiceValue(models.Model):
    list = models.ForeignKey(ChoiceList, on_delete=models.CASCADE, related_name="values")
    value = models.CharField(max_length=150)
    label = models.CharField(max_length=150)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_by_sync = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["list", "value"], name="unique_choicelist_value")]
        ordering = ["sort_order", "label"]

    def __str__(self):
        return f"{self.list.key}:{self.value}"


class UserCapability(models.Model):
    """An explicit override of one named capability for one user (Phase 15B).
    Absence of a row means "use the role default" — see
    apps/settings_admin/capabilities.py:ROLE_DEFAULT_CAPABILITIES."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="capability_overrides"
    )
    capability = models.CharField(max_length=50)
    granted = models.BooleanField()
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "capability"], name="unique_user_capability")
        ]

    def __str__(self):
        return f"{self.user.email}:{self.capability}={'granted' if self.granted else 'revoked'}"


class NotificationPolicy(models.Model):
    """Admin-controlled default for one notification event (Phase 15C) — a
    user's own override (UserNotificationPolicyOverride) always wins."""

    event_key = models.SlugField(max_length=50, unique=True)
    label = models.CharField(max_length=150)
    default_in_app = models.BooleanField(default=True)
    default_email = models.BooleanField(default=False)
    applies_to_roles = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label


class UserNotificationPolicyOverride(models.Model):
    """Per-user override of a NotificationPolicy's defaults. `null` on either
    field means "inherit the policy default for that channel" — stored this
    way (rather than always-on/off) so a later change to the policy default
    only affects users who never touched their own setting."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_policy_overrides"
    )
    policy = models.ForeignKey(NotificationPolicy, on_delete=models.CASCADE, related_name="user_overrides")
    in_app = models.BooleanField(null=True, blank=True)
    email = models.BooleanField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "policy"], name="unique_user_policy_override")
        ]


class DeadlineReminderRule(models.Model):
    days_before = models.PositiveIntegerField(unique=True)
    is_active = models.BooleanField(default=False)
    applies_to_roles = models.JSONField(default=list, blank=True)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="extra_deadline_reminder_rules"
    )

    class Meta:
        ordering = ["days_before"]

    def __str__(self):
        return f"{self.days_before}-day reminder"


class WelcomeEmailSettings(models.Model):
    """Global on/off switch for the Phase 20 welcome-email feature — a
    single-row singleton, default OFF. Nothing sends until an admin turns
    this on, regardless of who clicks "Send" (§Phase 20 item 5)."""

    enabled = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Welcome emails: {'on' if self.enabled else 'off'}"


class SheetAppendSettings(models.Model):
    """Global on/off switch for the Phase 23 append-only sheet write-back — a
    single-row singleton, default OFF, same pattern as WelcomeEmailSettings.
    Checked both here (for the settings UI) and again inside
    apps.sync.append.append_bid_to_sheet itself, so the gate holds no matter
    what calls it (create-bid flow or the periodic retry sweep)."""

    enabled = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Sheet append: {'on' if self.enabled else 'off'}"


class SyncScheduleSettings(models.Model):
    """Admin-configurable interval for the automatic scheduled sync — a
    single-row singleton, default 8 hours (matching the original fixed
    0/8/16 Dhaka schedule). Celery Beat itself still ticks frequently (every
    15 minutes, config/settings/base.py); apps.sync.tasks.sync_sheet_task
    checks this value against the last scheduled run's start time and only
    actually syncs once that many hours have elapsed — so a change here
    takes effect on the next tick, no restart needed. Manual "Fetch data"
    triggers are never gated by this — only the automatic schedule is."""

    interval_hours = models.PositiveIntegerField(default=8)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Sync every {self.interval_hours}h"


class EmailServiceSettings(models.Model):
    """Global kill switch for all outbound email — a single-row singleton,
    default ON (email already works today; this is an override, not an
    opt-in). Checked at both real send paths (apps.notifications.emails._send
    and apps.accounts.views._send_password_reset_email, which bypasses that
    helper entirely) — turning this off logs every attempt to SentEmail as a
    failure with a clear reason, rather than either silently sending or
    silently vanishing. Never affects in-app notifications, only email."""

    enabled = models.BooleanField(default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Email service: {'on' if self.enabled else 'off'}"


class DeadlineReminderSent(models.Model):
    """Per-bid-per-rule dedup (§16's old single `deadline_alert_sent_at`
    couldn't represent "already sent the 7-day one but not the 14-day one")."""

    bid = models.ForeignKey("bids.Bid", on_delete=models.CASCADE, related_name="deadline_reminders_sent")
    rule = models.ForeignKey(DeadlineReminderRule, on_delete=models.CASCADE, related_name="sent_records")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["bid", "rule"], name="unique_bid_rule_reminder_sent")
        ]
