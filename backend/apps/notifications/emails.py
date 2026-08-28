from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def _send(subject, template_prefix, context, to_email):
    context = {**context, "unsubscribe_url": f"{settings.FRONTEND_BASE_URL}/notifications"}
    text_body = render_to_string(f"notifications/{template_prefix}.txt", context)
    html_body = render_to_string(f"notifications/{template_prefix}.html", context)
    message = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [to_email])
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=True)


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
