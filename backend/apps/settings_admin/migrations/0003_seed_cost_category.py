"""Seeds the ChoiceList for BidCostLine.category (§Phase 19 item 2). Unlike
the 8 lists in 0002, this one has no sheet data to derive values from — it's
a wholly new, app-native field — so it starts with zero ChoiceValue rows;
an admin adds categories (Printing, Travel, Documentation, ...) from scratch
via the existing generic "Add value" UI (Phase 16), keyed by list_key.

ChoiceList rows can only ever be seeded by migration, never created through
the API (see settings_admin/views.py's ChoiceListViewSet) — so this migration
is what makes the category admin-manageable at all.
"""

from django.db import migrations

CATEGORY_KEY = "cost_category"
CATEGORY_LABEL = "Cost category"


def seed(apps, schema_editor):
    ChoiceList = apps.get_model("settings_admin", "ChoiceList")
    ChoiceList.objects.get_or_create(
        key=CATEGORY_KEY, defaults={"label": CATEGORY_LABEL, "is_locked": True}
    )


def unseed(apps, schema_editor):
    ChoiceList = apps.get_model("settings_admin", "ChoiceList")
    ChoiceList.objects.filter(key=CATEGORY_KEY).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("settings_admin", "0002_seed_choice_lists_and_policies"),
        ("bids", "0005_engagement_and_cost_tracking"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
