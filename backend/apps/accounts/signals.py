"""Bridges django-axes' lockout signal into the app's own audit trail — axes
tracks failed-login counts itself, but §15's append-only AuditEntry log is
the one place admins actually look, so a lockout needs to show up there too.
Connected from AccountsConfig.ready() rather than decorated here, since axes
must already be installed/imported before we can reference its signal.
"""


def log_lockout_to_audit(request, username, ip_address, **kwargs):
    from apps.audit.models import AuditEntry

    AuditEntry.objects.create(
        actor=None,
        actor_label=username or "unknown",
        action=AuditEntry.Action.ACCOUNT_LOCKOUT,
        ip=ip_address,
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
    )
