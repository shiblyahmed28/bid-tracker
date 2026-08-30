import pytest

from apps.accounts.admin import UserCreationAdminForm
from apps.accounts.models import User
from apps.accounts.serializers import ProfileSerializer, UserSerializer


@pytest.mark.django_db
class TestModelHasNoDomainRestriction:
    """§Phase 21 item 1 — admins may create accounts on any domain, so the
    restriction can no longer live on the model field itself (every writer
    shares one model). It's enforced per-serializer instead."""

    def test_model_accepts_company_email(self):
        user = User(email="someone@spectrum-bd.com", full_name="Someone", role=User.Role.VIEWER)
        user.set_password("Password123!")
        user.full_clean()  # must not raise

    def test_model_accepts_any_domain(self):
        user = User(email="someone@gmail.com", full_name="Someone", role=User.Role.VIEWER)
        user.set_password("Password123!")
        user.full_clean()  # must not raise — the model itself is domain-agnostic now

    def test_is_external_property(self):
        assert User(email="someone@gmail.com").is_external is True
        assert User(email="someone@spectrum-bd.com").is_external is False
        assert User(email="SOMEONE@SPECTRUM-BD.COM").is_external is False  # case-insensitive


@pytest.mark.django_db
class TestUserSerializerExternalAccounts:
    """UserSerializer backs the admin-only /users/ endpoint (already gated by
    manage_users) — any domain is allowed, but an external-domain account
    must be a viewer and can't be promoted."""

    def test_accepts_any_domain_with_default_role(self):
        serializer = UserSerializer(data={"email": "someone@gmail.com", "password": "Password123!"})
        assert serializer.is_valid(), serializer.errors

    def test_accepts_company_email_with_any_role(self):
        serializer = UserSerializer(
            data={"email": "someone@spectrum-bd.com", "password": "Password123!", "role": User.Role.ADMIN}
        )
        assert serializer.is_valid(), serializer.errors

    def test_external_domain_with_viewer_role_is_accepted(self):
        serializer = UserSerializer(
            data={"email": "someone@gmail.com", "password": "Password123!", "role": User.Role.VIEWER}
        )
        assert serializer.is_valid(), serializer.errors

    def test_external_domain_with_editor_role_is_rejected(self):
        serializer = UserSerializer(
            data={"email": "someone@gmail.com", "password": "Password123!", "role": User.Role.EDITOR}
        )
        assert serializer.is_valid() is False
        assert "role" in serializer.errors

    def test_external_domain_with_admin_role_is_rejected(self):
        serializer = UserSerializer(
            data={"email": "someone@gmail.com", "password": "Password123!", "role": User.Role.ADMIN}
        )
        assert serializer.is_valid() is False
        assert "role" in serializer.errors

    def test_cannot_promote_an_existing_external_account(self):
        user = User.objects.create_user(email="ext@gmail.com", password="x", role=User.Role.VIEWER)
        serializer = UserSerializer(user, data={"role": User.Role.EDITOR}, partial=True)
        assert serializer.is_valid() is False
        assert "role" in serializer.errors

    def test_can_edit_other_fields_of_an_existing_external_account(self):
        user = User.objects.create_user(email="ext2@gmail.com", password="x", role=User.Role.VIEWER)
        serializer = UserSerializer(user, data={"phone": "+880123"}, partial=True)
        assert serializer.is_valid(), serializer.errors

    def test_changing_a_company_account_to_an_external_email_forces_viewer_check(self):
        user = User.objects.create_user(email="was-company@spectrum-bd.com", password="x", role=User.Role.EDITOR)
        # Same request tries to move to an external domain while keeping editor — rejected.
        serializer = UserSerializer(user, data={"email": "now-external@gmail.com"}, partial=True)
        assert serializer.is_valid() is False
        assert "role" in serializer.errors


@pytest.mark.django_db
class TestProfileSerializerStaysCompanyDomainOnly:
    """Non-admins (and admins editing their own profile) stay restricted to
    the company domain — this is a self-service edit, distinct from
    UserSerializer's admin-managed accounts."""

    def test_rejects_a_new_non_company_email(self):
        user = User.objects.create_user(email="me@spectrum-bd.com", password="x", role=User.Role.VIEWER)
        serializer = ProfileSerializer(user, data={"email": "me@gmail.com"}, partial=True)
        assert serializer.is_valid() is False
        assert "email" in serializer.errors

    def test_accepts_a_new_company_email(self):
        user = User.objects.create_user(email="me@spectrum-bd.com", password="x", role=User.Role.VIEWER)
        serializer = ProfileSerializer(user, data={"email": "me-new@spectrum-bd.com"}, partial=True)
        assert serializer.is_valid(), serializer.errors

    def test_keeping_an_already_external_email_unchanged_is_allowed(self):
        """The bug this guards against: an admin-created external viewer
        must still be able to save their profile (e.g. just a phone number)
        without being blocked because their own existing email fails the
        company-domain check."""
        user = User.objects.create_user(email="ext@gmail.com", password="x", role=User.Role.VIEWER)
        serializer = ProfileSerializer(user, data={"email": "ext@gmail.com", "phone": "+880999"}, partial=True)
        assert serializer.is_valid(), serializer.errors

    def test_an_external_user_still_cannot_change_to_a_different_external_email(self):
        user = User.objects.create_user(email="ext3@gmail.com", password="x", role=User.Role.VIEWER)
        serializer = ProfileSerializer(user, data={"email": "ext3@yahoo.com"}, partial=True)
        assert serializer.is_valid() is False
        assert "email" in serializer.errors


@pytest.mark.django_db
class TestAdminCreateFormAllowsAnyDomain:
    """Django admin (superuser-only escape hatch) shares the same model, so
    it now allows any domain too — superusers are already fully trusted."""

    def test_admin_create_form_accepts_company_email(self):
        form = UserCreationAdminForm(
            data={"email": "someone@spectrum-bd.com", "password1": "Password123456!", "password2": "Password123456!"}
        )
        assert form.is_valid(), form.errors

    def test_admin_create_form_accepts_any_domain(self):
        form = UserCreationAdminForm(
            data={"email": "someone@gmail.com", "password1": "Password123456!", "password2": "Password123456!"}
        )
        assert form.is_valid(), form.errors
