from django.db import migrations

TEAMS = [
    "Government",
    "Banking & Fintech",
    "Education & Research",
    "Telecom",
    "Enterprise",
]


def seed_teams(apps, schema_editor):
    Team = apps.get_model("bids", "Team")
    for name in TEAMS:
        Team.objects.get_or_create(name=name)


def unseed_teams(apps, schema_editor):
    Team = apps.get_model("bids", "Team")
    Team.objects.filter(name__in=TEAMS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bids", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_teams, unseed_teams),
    ]
