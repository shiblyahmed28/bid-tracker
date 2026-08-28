from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from user_agents import parse as parse_ua


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")


def parse_user_agent(user_agent_string):
    """Best-effort device type, brand, OS and browser from a raw UA string (§14: never authoritative)."""
    from apps.accounts.models import UserSession

    ua = parse_ua(user_agent_string or "")

    if ua.is_mobile:
        device_type = UserSession.DeviceType.MOBILE
    elif ua.is_tablet:
        device_type = UserSession.DeviceType.TABLET
    elif ua.is_pc:
        device_type = UserSession.DeviceType.DESKTOP
    else:
        device_type = UserSession.DeviceType.UNKNOWN

    device_brand = ua.device.brand or ""

    os_name = ua.os.family or ""
    if ua.os.version_string:
        os_name = f"{os_name} {ua.os.version_string}".strip()

    browser = ua.browser.family or ""
    if ua.browser.version_string:
        browser = f"{browser} {ua.browser.version_string}".strip()

    return device_type, device_brand, os_name, browser


def blacklist_jti(jti, user=None, created_at=None):
    """Blacklist a refresh token by jti alone, when we don't hold the signed token
    (e.g. revoking someone else's session). expires_at is a safe upper-bound estimate —
    it only affects simplejwt's own cleanup command, not whether the jti is honoured.
    """
    expires_at = timezone.now() + settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    outstanding, _ = OutstandingToken.objects.get_or_create(
        jti=jti,
        defaults={"token": "", "user": user, "created_at": created_at, "expires_at": expires_at},
    )
    BlacklistedToken.objects.get_or_create(token=outstanding)
