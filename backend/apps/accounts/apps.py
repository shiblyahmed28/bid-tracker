from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        from axes.signals import user_locked_out

        from .signals import log_lockout_to_audit

        user_locked_out.connect(log_lockout_to_audit, dispatch_uid="accounts-audit-lockout")
