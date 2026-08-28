from django.conf import settings
from django.db import models


class AuditEntry(models.Model):
    """Append-only record of who changed what. No update or delete, ever — not even for admins."""

    class Action(models.TextChoices):
        SIGN_IN = "sign_in", "Sign in"
        SIGN_IN_FAILED = "sign_in_failed", "Failed sign in"
        SIGN_OUT = "sign_out", "Sign out"
        SESSION_REVOKE = "session_revoke", "Session revoked"
        BID_CREATE = "bid_create", "Bid created"
        BID_UPDATE = "bid_update", "Bid updated"
        BID_SOFT_DELETE = "bid_soft_delete", "Bid soft-deleted"
        BID_RESTORE = "bid_restore", "Bid restored"
        CONFLICT_RESOLUTION = "conflict_resolution", "Sync conflict resolved"
        USER_CREATE = "user_create", "User created"
        USER_UPDATE = "user_update", "User updated"
        ROLE_CHANGE = "role_change", "Role changed"
        PASSWORD_RESET = "password_reset", "Password reset"
        PASSWORD_CHANGE = "password_change", "Password changed"
        MANUAL_SYNC_TRIGGER = "manual_sync_trigger", "Manual sync triggered"
        CHOICE_VALUE_RENAME = "choice_value_rename", "Choice value renamed"
        CHOICE_VALUE_CREATE = "choice_value_create", "Choice value created"
        CHOICE_VALUE_UPDATE = "choice_value_update", "Choice value updated"
        CAPABILITY_GRANT = "capability_grant", "Capability granted"
        CAPABILITY_REVOKE = "capability_revoke", "Capability revoked"
        NOTIFICATION_POLICY_UPDATE = "notification_policy_update", "Notification policy updated"
        DEADLINE_RULE_UPDATE = "deadline_rule_update", "Deadline reminder rule updated"
        SETTINGS_CHANGE = "settings_change", "Master setting changed"

    # actor is null with actor_label="System (sync)" for automated changes.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    actor_label = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=32, choices=Action.choices)
    bid = models.ForeignKey(
        "bids.Bid",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    field = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "audit entries"

    def __str__(self):
        return f"{self.get_action_display()} by {self.actor_label or 'unknown'} at {self.created_at}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("AuditEntry is append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditEntry is append-only and cannot be deleted.")
