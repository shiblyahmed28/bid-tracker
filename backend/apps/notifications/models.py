from django.conf import settings
from django.db import models

# The subscribable Bid fields (§16) — every column except SL/description/
# remarks, mirroring frontend/src/register/columns.tsx's key set so the same
# names appear in the register, the notification settings page and here.
# Several real model fields collapse onto one conceptual key so a user gets
# exactly one notification per meaningful change, not one per raw field
# (e.g. security_amount/_raw/_currency are three fields but one concept).
NOTIFICATION_FIELDS = [
    ("client", "Client"),
    ("team", "Team"),
    ("stage", "Stage"),
    ("procurement_type", "Procurement type"),
    ("initiation_mode", "Initiation mode"),
    ("delivery_type", "Delivery type"),
    ("tender_id", "Tender ID"),
    ("cam", "CAM"),
    ("sales_resource", "Sales resource"),
    ("bid_manager", "Bid manager"),
    ("engaged_resources", "Engaged resources"),
    ("engagement_period", "Engagement period"),
    ("initiation_date", "Initiation date"),
    ("published_date", "Published"),
    ("prebid_date", "Pre-bid"),
    ("submission_date", "Submission"),
    ("security_mode", "Security mode"),
    ("security_amount", "Security amount"),
    ("credit_facility", "Credit facility"),
    ("bg_issue_date", "BG issue date"),
    ("bg_reference", "BG / reference no."),
    ("bg_bank", "Issuing bank"),
    ("bg_expiry_date", "BG expiry"),
    ("submission_status", "Submission status"),
    ("result", "Result"),
]
NOTIFICATION_FIELD_KEYS = {key for key, _label in NOTIFICATION_FIELDS}

# Real Bid.apply_change field names that collapse onto one conceptual key above.
RAW_FIELD_TO_NOTIFICATION_KEY = {
    "is_goods": "delivery_type",
    "is_works": "delivery_type",
    "is_service": "delivery_type",
    "security_amount_raw": "security_amount",
    "security_currency": "security_amount",
    "credit_facility_raw": "credit_facility",
    "credit_facility_currency": "credit_facility",
    "engagement_from": "engagement_period",
    "engagement_to": "engagement_period",
}

DEFAULT_ON_FIELDS = {
    "result",
    "submission_status",
    "submission_date",
    "security_amount",
    "bg_expiry_date",
    "bid_manager",
    "team",
    "engaged_resources",
}


def notification_key_for(raw_field_name):
    """Maps a raw Bid.apply_change field name to its conceptual notification
    key, or None if that raw field isn't user-facing (shouldn't happen for
    any field apply_change is ever called with)."""
    key = RAW_FIELD_TO_NOTIFICATION_KEY.get(raw_field_name, raw_field_name)
    return key if key in NOTIFICATION_FIELD_KEYS else None


class NotificationSubscription(models.Model):
    """A user's explicit override of one field's default-on/off state (§16).
    Absence of a row means "use the default" — see DEFAULT_ON_FIELDS."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_subscriptions"
    )
    field_name = models.CharField(max_length=50)
    enabled = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "field_name"], name="unique_user_field_subscription")
        ]

    def __str__(self):
        return f"{self.user.email} · {self.field_name} · {'on' if self.enabled else 'off'}"


class Notification(models.Model):
    class Kind(models.TextChoices):
        NEW_BID = "new_bid", "New bid"
        FIELD_CHANGE = "field_change", "Field changed"
        DEADLINE = "deadline", "Deadline approaching"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    bid = models.ForeignKey(
        "bids.Bid", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} → {self.user.email}: {self.title}"


class SentEmail(models.Model):
    """One row per outbound email attempt, success or failure (§Phase 21 item
    4) — the "did that person get notified?" log, admin-only. Deliberately
    carries no body/content field at all: several of these templates (new_bid,
    deadline, policy_event, welcome_engagement) can include financial detail,
    and never storing the body is a stronger guarantee than trying to scrub
    or pattern-match "financial" content out of it after the fact."""

    class Kind(models.TextChoices):
        NEW_BID = "new_bid", "New bid"
        DEADLINE = "deadline", "Deadline reminder"
        POLICY_EVENT = "policy_event", "Policy event"
        DIGEST = "digest", "Digest"
        WELCOME_ENGAGEMENT = "welcome_engagement", "Welcome email"
        PASSWORD_RESET = "password_reset", "Password reset"

    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    kind = models.CharField(max_length=30, choices=Kind.choices)
    bid = models.ForeignKey(
        "bids.Bid", null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_emails"
    )
    success = models.BooleanField()
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.to_email} · {self.get_kind_display()} · {'sent' if self.success else 'failed'}"


class PendingDigestItem(models.Model):
    """One row per (user, changed field) queued since that user's last digest
    email — batched into a single email per user per sync run (§9 step 7,
    §16), consumed and deleted by send_pending_digests()."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pending_digest_items")
    bid = models.ForeignKey("bids.Bid", on_delete=models.CASCADE, related_name="pending_digest_items")
    field_name = models.CharField(max_length=50)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
