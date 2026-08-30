from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import UserManager
from .validators import is_external_domain


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    username = None
    # No domain validator here (§Phase 21 item 1) — admins may create accounts
    # on any domain now. The company-domain restriction lives in
    # ProfileSerializer.validate_email (self-service profile edits only, for
    # every role including admin) and UserSerializer.validate (external
    # accounts forced to viewer), not on the model, since the same field
    # needs different rules depending on who's writing to it.
    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)
    must_change_password = models.BooleanField(default=False)

    notifications_muted = models.BooleanField(default=False)
    email_digest = models.BooleanField(default=True)
    email_deadline = models.BooleanField(default=True)
    email_newbid = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_external(self):
        """§Phase 21 item 1 — an account whose email isn't on the company
        domain. Forced to viewer and un-promotable (UserSerializer.validate);
        badged in the Users list."""
        return is_external_domain(self.email)

    @property
    def is_editor_or_above(self):
        return self.role in (self.Role.ADMIN, self.Role.EDITOR)

    def has_capability(self, capability):
        """Named capability on top of role (§Phase 15B) — an explicit
        UserCapability override wins, otherwise the role default applies."""
        from apps.settings_admin.capabilities import user_has_capability

        return user_has_capability(self, capability)


class UserSession(models.Model):
    """One row per login. `refresh_jti` tracks the *currently* valid refresh
    token for this session — it is updated on every rotation so revocation
    (which blacklists by jti) actually stops the live token, not a stale one.
    """

    class DeviceType(models.TextChoices):
        DESKTOP = "desktop", "Desktop"
        MOBILE = "mobile", "Mobile"
        TABLET = "tablet", "Tablet"
        UNKNOWN = "unknown", "Unknown"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions"
    )
    refresh_jti = models.CharField(max_length=64, unique=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(
        max_length=10, choices=DeviceType.choices, default=DeviceType.UNKNOWN
    )
    device_brand = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} · {self.device_type} · {self.browser}"

    @property
    def is_active(self):
        if self.revoked_at is not None:
            return False
        lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
        return timezone.now() < self.last_seen_at + lifetime
