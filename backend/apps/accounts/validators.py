from django.conf import settings
from django.core.validators import RegexValidator

email_domain_validator = RegexValidator(
    regex=r"^[^@\s]+@" + settings.ALLOWED_EMAIL_DOMAIN.replace(".", r"\.") + r"$",
    message=f"Only @{settings.ALLOWED_EMAIL_DOMAIN} email addresses are allowed.",
)
