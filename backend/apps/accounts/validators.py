from django.conf import settings
from django.core.validators import RegexValidator


def is_external_domain(email):
    """True if `email`'s domain isn't the company one (§Phase 21 item 1).
    Used both to force external accounts to viewer and to badge them in the
    Users list."""
    if not email or "@" not in email:
        return True
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return domain != settings.ALLOWED_EMAIL_DOMAIN.lower()


# Still used by ProfileSerializer — a self-service profile edit always stays
# restricted to the company domain, for every role including admin
# (§Phase 21 item 1: "non-admins remain restricted... for their own
# profile" — nothing carves out an exception for admins' own profiles either,
# only for the accounts *they create for other people*, via UserSerializer).
email_domain_validator = RegexValidator(
    regex=r"^[^@\s]+@" + settings.ALLOWED_EMAIL_DOMAIN.replace(".", r"\.") + r"$",
    message=f"Only @{settings.ALLOWED_EMAIL_DOMAIN} email addresses are allowed.",
)
