from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager
from .validators import email_domain_validator


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    username = None
    email = models.EmailField(
        "email address", unique=True, validators=[email_domain_validator]
    )
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)
    must_change_password = models.BooleanField(default=False)

    notifications_muted = models.BooleanField(default=False)
    email_digest = models.BooleanField(default=True)
    email_deadline = models.BooleanField(default=True)
    email_newbid = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_editor_or_above(self):
        return self.role in (self.Role.ADMIN, self.Role.EDITOR)
