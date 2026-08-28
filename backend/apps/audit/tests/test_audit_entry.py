import pytest

from apps.audit.models import AuditEntry


@pytest.mark.django_db
def test_audit_entry_cannot_be_modified_after_creation():
    entry = AuditEntry.objects.create(
        action=AuditEntry.Action.SIGN_IN, actor_label="someone@spectrum-bd.com"
    )
    entry.action = AuditEntry.Action.SIGN_OUT
    with pytest.raises(ValueError):
        entry.save()


@pytest.mark.django_db
def test_audit_entry_cannot_be_deleted():
    entry = AuditEntry.objects.create(
        action=AuditEntry.Action.SIGN_IN, actor_label="someone@spectrum-bd.com"
    )
    with pytest.raises(ValueError):
        entry.delete()
