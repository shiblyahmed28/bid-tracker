"""Deployment settings — set DJANGO_SETTINGS_MODULE=config.settings.production
to use this. Forces DEBUG off (which also disables the Django admin — see
config/urls.py), requires ALLOWED_HOSTS/CORS to be configured explicitly
rather than silently defaulting, and turns on the full security header set.
Nothing here changes application/business logic — see base.py for that."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be set explicitly when running with "
        "config.settings.production."
    )

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
if not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS must be set explicitly when running with "
        "config.settings.production."
    )

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        "CSRF_TRUSTED_ORIGINS must be set explicitly when running with "
        "config.settings.production."
    )

# Caddy/web is the only thing in front of the app; it always sets
# X-Forwarded-Proto, whether the deployment is running plain HTTP on :8090
# (pre-TLS verification, TLS_ENABLED=0) or terminating TLS on :443
# (TLS_ENABLED=1) — see docs/DEPLOY.md for the two-step rollout this
# supports. Only the secure-cookie/HSTS settings, which would break the
# plain-HTTP verification step outright, are gated on the flag.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

TLS_ENABLED = env.bool("TLS_ENABLED", default=False)

if TLS_ENABLED:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True

    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Web (Caddy) reverse-proxies /static/ to gunicorn rather than serving it
# from a shared volume, so gunicorn needs to actually serve those files —
# runserver does this automatically in DEBUG, plain WSGI does not.
MIDDLEWARE.insert(  # noqa: F405 — MIDDLEWARE comes from base.py's `import *`
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,  # noqa: F405
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
