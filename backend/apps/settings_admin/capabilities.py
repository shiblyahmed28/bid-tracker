"""Named capabilities layered on top of roles (§Phase 15B). Kept dependency-free
of models.py's app config so apps/accounts/models.py can import it without a
circular import (accounts -> settings_admin at call time only, never at
module load)."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

CAPABILITIES = [
    "access_master_settings",
    "manage_users",
    "view_audit_log",
    "view_sync_history",
    "trigger_sync",
    "manage_choice_lists",
    "manage_notification_policy",
    "delete_bid",
    "export_pdf",
    "create_bid",
    "edit_bid",
]

ROLE_DEFAULT_CAPABILITIES = {
    "viewer": {"export_pdf"},
    "editor": {"export_pdf", "create_bid", "edit_bid"},
    "admin": set(CAPABILITIES),
}

# An admin can't strip these off their own account — see settings_admin/services.py.
SELF_LOCKOUT_PROTECTED_CAPABILITIES = {"manage_users", "access_master_settings"}


def role_default_capabilities(role):
    return ROLE_DEFAULT_CAPABILITIES.get(role, set())


def user_has_capability(user, capability):
    """Explicit per-user override wins; otherwise fall back to the role
    default. `user.has_capability(name)` on the User model just calls this."""
    override = user.capability_overrides.filter(capability=capability).first()
    if override is not None:
        return override.granted
    return capability in role_default_capabilities(user.role)


def HasCapability(capability):
    """DRF permission factory — `permission_classes = [HasCapability("delete_bid")]`."""

    class _HasCapability(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            return bool(
                user and user.is_authenticated and user.is_active and user.has_capability(capability)
            )

    _HasCapability.__name__ = f"HasCapability_{capability}"
    return _HasCapability


def SettingsPermission(write_capability=None):
    """Every /settings/ endpoint requires access_master_settings just to be
    reached (§Phase 15D); a write action (anything but GET/HEAD/OPTIONS) can
    additionally require a more specific capability, e.g. manage_choice_lists."""

    class _SettingsPermission(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            if not (user and user.is_authenticated and user.is_active):
                return False
            if not user.has_capability("access_master_settings"):
                return False
            if write_capability is None or request.method in SAFE_METHODS:
                return True
            return user.has_capability(write_capability)

    _SettingsPermission.__name__ = f"SettingsPermission_{write_capability}"
    return _SettingsPermission
