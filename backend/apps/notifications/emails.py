from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import SentEmail


def _send(subject, template_prefix, context, to_email, include_unsubscribe=True):
    """include_unsubscribe=False for recipients with no login account to
    manage (e.g. welcome_engagement's Person recipients, §Phase 20 item 5) —
    _base.html only renders the footer link when unsubscribe_url is present.

    Logs a SentEmail row for every attempt (§Phase 21 item 4) — success or
    failure — never the rendered body. `fail_silently` used to swallow send
    errors entirely with no record of them; catching the exception here
    keeps that same external behavior (callers still never see it raised)
    while capturing the error message for the log."""
    if include_unsubscribe:
        context = {**context, "unsubscribe_url": f"{settings.FRONTEND_BASE_URL}/notifications"}
    text_body = render_to_string(f"notifications/{template_prefix}.txt", context)
    html_body = render_to_string(f"notifications/{template_prefix}.html", context)
    message = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [to_email])
    message.attach_alternative(html_body, "text/html")

    try:
        message.send(fail_silently=False)
        SentEmail.objects.create(
            to_email=to_email, subject=subject, kind=template_prefix, bid=context.get("bid"), success=True
        )
    except Exception as exc:
        SentEmail.objects.create(
            to_email=to_email,
            subject=subject,
            kind=template_prefix,
            bid=context.get("bid"),
            success=False,
            error=str(exc),
        )


def send_new_bid_email(user, bid):
    _send(f"New bid — {bid.client.name}", "new_bid", {"user": user, "bid": bid}, user.email)


def send_deadline_email(user, bid, days_before=7):
    _send(
        f"Deadline in {days_before} days — {bid.client.name}",
        "deadline",
        {"user": user, "bid": bid, "days_before": days_before},
        user.email,
    )


def send_digest_email(user, items):
    _send("Your Spectrum Bid Tracker digest", "digest", {"user": user, "items": items}, user.email)


def send_policy_event_email(user, bid, policy):
    _send(f"{policy.label} — {bid.client.name}", "policy_event", {"user": user, "bid": bid, "policy": policy}, user.email)


def send_welcome_engagement_email(engagement):
    """§Phase 20 item 5. External recipients get a reduced version — the
    financial/security/BG keys are simply absent from `context` for them, not
    just hidden by a template conditional, so a template bug can't leak them
    (§Phase 20: "External people must never receive commercially sensitive
    content by email")."""
    bid = engagement.bid
    person = engagement.person
    contact = bid.bid_manager or bid.cam or bid.sales_resource

    context = {
        "person": person,
        "bid": bid,
        "engagement": engagement,
        "contact": contact,
        "is_external": person.person_type == person.PersonType.EXTERNAL,
    }
    if person.person_type != person.PersonType.EXTERNAL:
        context.update(
            {
                "security_amount_raw": bid.security_amount_raw,
                "security_currency": bid.security_currency,
                "credit_facility_raw": bid.credit_facility_raw,
                "bg_bank": bid.bg_bank,
                "bg_reference": bid.bg_reference,
                "bg_expiry_date": bid.bg_expiry_date,
            }
        )

    _send(
        f"Welcome to {bid.client.name} — {bid.reference}",
        "welcome_engagement",
        context,
        person.email,
        include_unsubscribe=False,
    )
