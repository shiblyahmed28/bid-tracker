from django.core.management.base import BaseCommand

from apps.accounts.models import User

SEED = [
    {
        "email": "admin@spectrum-bd.com",
        "password": "AdminPass123!",
        "full_name": "Seed Admin",
        "role": User.Role.ADMIN,
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "email": "editor@spectrum-bd.com",
        "password": "EditorPass123!",
        "full_name": "Seed Editor",
        "role": User.Role.EDITOR,
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "email": "viewer@spectrum-bd.com",
        "password": "ViewerPass123!",
        "full_name": "Seed Viewer",
        "role": User.Role.VIEWER,
        "is_staff": False,
        "is_superuser": False,
    },
]


class Command(BaseCommand):
    help = "Create one admin, one editor and one viewer with known passwords for local development."

    def handle(self, *args, **options):
        for entry in SEED:
            password = entry["password"]
            user, created = User.objects.update_or_create(
                email=entry["email"],
                defaults={
                    "full_name": entry["full_name"],
                    "role": entry["role"],
                    "is_staff": entry["is_staff"],
                    "is_superuser": entry["is_superuser"],
                },
            )
            user.set_password(password)
            user.save()
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb} {entry['role']}: {entry['email']} / {password}"))
