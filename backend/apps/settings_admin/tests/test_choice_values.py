import pytest

from apps.audit.models import AuditEntry
from apps.bids.models import Bid, Client
from apps.settings_admin.models import ChoiceList, ChoiceValue
from apps.settings_admin.services import grant_capability, rename_value, sync_choice_values_from_bids

from conftest import login


@pytest.fixture
def client_obj(db):
    return Client.objects.create(name="Rename Test Co", canonical_name="rename test co")


@pytest.fixture
def stage_list(db):
    return ChoiceList.objects.get(key="stage")


@pytest.mark.django_db
def test_backfill_migration_created_lists_from_real_data():
    # Real synced sheet data should already be present from the data migration.
    assert ChoiceList.objects.filter(key="stage").exists()
    assert ChoiceList.objects.get(key="delivery_type").values.count() == 3


@pytest.mark.django_db
def test_rename_value_updates_every_bid_and_writes_audit_entry(stage_list, client_obj, admin_user):
    value = ChoiceValue.objects.create(list=stage_list, value="TENDER-TYPO", label="TENDER-TYPO")
    bid1 = Bid.objects.create(client=client_obj, stage="TENDER-TYPO", submission_date="2026-09-01")
    bid2 = Bid.objects.create(client=client_obj, stage="TENDER-TYPO", submission_date="2026-09-02")
    other = Bid.objects.create(client=client_obj, stage="EOI", submission_date="2026-09-03")

    updated = rename_value(value, "TENDER", "Tender", admin_user)

    assert updated == 2
    bid1.refresh_from_db()
    bid2.refresh_from_db()
    other.refresh_from_db()
    assert bid1.stage == "TENDER"
    assert bid2.stage == "TENDER"
    assert other.stage == "EOI"  # untouched

    value.refresh_from_db()
    assert value.value == "TENDER"
    assert value.label == "Tender"

    entry = AuditEntry.objects.filter(action=AuditEntry.Action.CHOICE_VALUE_RENAME).latest("created_at")
    assert entry.actor == admin_user
    assert entry.old_value == "TENDER-TYPO"
    assert entry.new_value == "TENDER"


@pytest.mark.django_db
def test_rename_value_on_delivery_type_touches_no_bid_rows(client_obj, admin_user):
    delivery_list = ChoiceList.objects.get(key="delivery_type")
    goods_value = delivery_list.values.get(value="goods")
    bid = Bid.objects.create(client=client_obj, is_goods=True, submission_date="2026-09-01")

    updated = rename_value(goods_value, "goods", "Materials", admin_user)

    assert updated == 0  # no free-text column to update
    bid.refresh_from_db()
    assert bid.is_goods is True  # structural flag untouched
    goods_value.refresh_from_db()
    assert goods_value.label == "Materials"


@pytest.mark.django_db
def test_deactivating_a_value_leaves_existing_bids_intact(stage_list, client_obj):
    value = ChoiceValue.objects.create(list=stage_list, value="EOI", label="EOI", is_active=True)
    bid = Bid.objects.create(client=client_obj, stage="EOI", submission_date="2026-09-01")

    value.is_active = False
    value.save(update_fields=["is_active"])

    bid.refresh_from_db()
    assert bid.stage == "EOI"  # completely unaffected


@pytest.mark.django_db
def test_sync_choice_values_from_bids_autocreates_new_value_flagged_for_review(stage_list, client_obj):
    Bid.objects.create(client=client_obj, stage="BRAND-NEW-STAGE", submission_date="2026-09-01")

    created = sync_choice_values_from_bids()

    assert ("stage", "BRAND-NEW-STAGE") in created
    value = ChoiceValue.objects.get(list=stage_list, value="BRAND-NEW-STAGE")
    assert value.created_by_sync is True
    assert value.is_active is True


@pytest.mark.django_db
def test_sync_choice_values_from_bids_is_idempotent(stage_list, client_obj):
    Bid.objects.create(client=client_obj, stage="ANOTHER-NEW-ONE", submission_date="2026-09-01")
    first = sync_choice_values_from_bids()
    second = sync_choice_values_from_bids()
    assert ("stage", "ANOTHER-NEW-ONE") in first
    assert second == []


@pytest.mark.django_db
def test_label_only_edit_still_writes_audit_entry(api_client, admin_user, stage_list):
    """Every mutation writes an audit entry — not just deactivation."""
    value = ChoiceValue.objects.create(list=stage_list, value="RFQ", label="RFQ")
    before = AuditEntry.objects.filter(action=AuditEntry.Action.CHOICE_VALUE_UPDATE).count()

    login(api_client, admin_user, "AdminPass123!")
    response = api_client.patch(
        f"/api/v1/settings/choice-lists/stage/values/{value.id}/", {"label": "Request for Quotation"}, format="json"
    )

    assert response.status_code == 200
    after = AuditEntry.objects.filter(action=AuditEntry.Action.CHOICE_VALUE_UPDATE).count()
    assert after == before + 1


@pytest.mark.django_db
def test_rename_value_via_api_and_deactivate_via_api(api_client, admin_user, stage_list, client_obj):
    value = ChoiceValue.objects.create(list=stage_list, value="OLDVAL", label="OLDVAL")
    Bid.objects.create(client=client_obj, stage="OLDVAL", submission_date="2026-09-01")

    login(api_client, admin_user, "AdminPass123!")
    rename_response = api_client.post(
        f"/api/v1/settings/choice-lists/stage/values/{value.id}/rename/",
        {"new_value": "NEWVAL", "new_label": "New Val"},
        format="json",
    )
    assert rename_response.status_code == 200
    assert rename_response.data["updated_bids"] == 1

    deactivate_response = api_client.patch(
        f"/api/v1/settings/choice-lists/stage/values/{value.id}/", {"is_active": False}, format="json"
    )
    assert deactivate_response.status_code == 200
    value.refresh_from_db()
    assert value.is_active is False


@pytest.mark.django_db
def test_viewer_with_access_master_settings_but_not_manage_choice_lists_gets_403_on_write(
    api_client, viewer, admin_user, stage_list
):
    grant_capability(viewer, "access_master_settings", True, admin_user)
    login(api_client, viewer, "ViewerPass123!")

    read_response = api_client.get("/api/v1/settings/choice-lists/stage/values/")
    assert read_response.status_code == 200

    write_response = api_client.post(
        "/api/v1/settings/choice-lists/stage/values/", {"value": "X", "label": "X"}, format="json"
    )
    assert write_response.status_code == 403
