"""§Phase 21 item 3 — Gmail rewrites or rejects a From: address whose domain
doesn't match the authenticated SMTP account, unless that domain is a
verified "Send mail as" alias (see docs/DEPLOY.md). Warn loudly at startup
rather than let every send quietly misbehave.
"""

from django.conf import settings
from django.core.checks import Warning, register


def _domain(email_address):
    """Extracts the domain from a plain address or a "Name <addr>" form."""
    if "<" in email_address and ">" in email_address:
        email_address = email_address.split("<", 1)[1].split(">", 1)[0]
    return email_address.rsplit("@", 1)[-1].strip().lower() if "@" in email_address else ""


@register()
def check_default_from_email_matches_smtp_account(app_configs, **kwargs):
    if not settings.EMAIL_HOST_USER:
        return []  # console backend (dev, no App Password configured) — nothing sends for real

    from_domain = _domain(settings.DEFAULT_FROM_EMAIL)
    smtp_domain = _domain(settings.EMAIL_HOST_USER)

    if from_domain and smtp_domain and from_domain != smtp_domain:
        return [
            Warning(
                f"DEFAULT_FROM_EMAIL's domain ({from_domain!r}) does not match the authenticated "
                f"SMTP account's domain ({smtp_domain!r}). Gmail will rewrite or reject the From: "
                "address unless that domain is registered as a verified 'Send mail as' alias on "
                "this account — see docs/DEPLOY.md.",
                id="notifications.W001",
            )
        ]
    return []
