"""§Phase 21 item 3 — the startup check warning when DEFAULT_FROM_EMAIL's
domain doesn't match the authenticated SMTP account's domain."""

from apps.notifications.checks import check_default_from_email_matches_smtp_account


def test_warns_when_domains_mismatch(settings):
    settings.EMAIL_HOST_USER = "someone@gmail.com"
    settings.DEFAULT_FROM_EMAIL = "Spectrum Bid Tracker <noreply@spectrum-bd.com>"
    errors = check_default_from_email_matches_smtp_account(None)
    assert len(errors) == 1
    assert errors[0].id == "notifications.W001"


def test_silent_when_domains_match(settings):
    settings.EMAIL_HOST_USER = "noreply@spectrum-bd.com"
    settings.DEFAULT_FROM_EMAIL = "Spectrum Bid Tracker <noreply@spectrum-bd.com>"
    assert check_default_from_email_matches_smtp_account(None) == []


def test_silent_when_smtp_user_is_a_verified_alias_on_the_same_domain(settings):
    settings.EMAIL_HOST_USER = "someone@spectrum-bd.com"
    settings.DEFAULT_FROM_EMAIL = "noreply@spectrum-bd.com"
    assert check_default_from_email_matches_smtp_account(None) == []


def test_silent_when_no_smtp_account_configured(settings):
    """Console backend (dev, no App Password) — nothing sends for real."""
    settings.EMAIL_HOST_USER = ""
    settings.DEFAULT_FROM_EMAIL = "noreply@spectrum-bd.com"
    assert check_default_from_email_matches_smtp_account(None) == []
