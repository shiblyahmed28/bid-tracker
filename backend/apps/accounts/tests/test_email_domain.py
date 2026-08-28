import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.accounts.admin import UserCreationAdminForm
from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer


@pytest.mark.django_db
def test_model_rejects_non_company_email():
    user = User(email="someone@gmail.com", full_name="Someone", role=User.Role.VIEWER)
    user.set_password("Password123!")
    with pytest.raises(DjangoValidationError):
        user.full_clean()


@pytest.mark.django_db
def test_model_accepts_company_email():
    user = User(email="someone@spectrum-bd.com", full_name="Someone", role=User.Role.VIEWER)
    user.set_password("Password123!")
    user.full_clean()  # must not raise


@pytest.mark.django_db
def test_serializer_rejects_non_company_email():
    serializer = UserSerializer(
        data={"email": "someone@gmail.com", "password": "Password123!", "role": User.Role.VIEWER}
    )
    assert serializer.is_valid() is False
    assert "email" in serializer.errors


@pytest.mark.django_db
def test_serializer_accepts_company_email():
    serializer = UserSerializer(
        data={"email": "someone@spectrum-bd.com", "password": "Password123!", "role": User.Role.VIEWER}
    )
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_admin_create_form_rejects_non_company_email():
    form = UserCreationAdminForm(
        data={
            "email": "someone@gmail.com",
            "password1": "Password123456!",
            "password2": "Password123456!",
        }
    )
    assert form.is_valid() is False
    assert "email" in form.errors


@pytest.mark.django_db
def test_admin_create_form_accepts_company_email():
    form = UserCreationAdminForm(
        data={
            "email": "someone@spectrum-bd.com",
            "password1": "Password123456!",
            "password2": "Password123456!",
        }
    )
    assert form.is_valid(), form.errors
