from types import SimpleNamespace

import pytest

from apps.accounts.models import User
from apps.accounts.permissions import IsAdmin, IsAuthenticatedViewer, IsEditorOrAbove


def make_user(role):
    return User.objects.create_user(
        email=f"{role}-perm@spectrum-bd.com", password="Password123!", role=role
    )


@pytest.mark.django_db
def test_is_authenticated_viewer_allows_every_role():
    perm = IsAuthenticatedViewer()
    for role in (User.Role.ADMIN, User.Role.EDITOR, User.Role.VIEWER):
        request = SimpleNamespace(user=make_user(role))
        assert perm.has_permission(request, None) is True


@pytest.mark.django_db
def test_is_authenticated_viewer_denies_anonymous():
    from django.contrib.auth.models import AnonymousUser

    perm = IsAuthenticatedViewer()
    request = SimpleNamespace(user=AnonymousUser())
    assert perm.has_permission(request, None) is False


@pytest.mark.django_db
def test_is_editor_or_above_denies_viewer_allows_editor_and_admin():
    perm = IsEditorOrAbove()
    viewer = make_user(User.Role.VIEWER)
    editor = make_user(User.Role.EDITOR)
    admin = make_user(User.Role.ADMIN)

    assert perm.has_permission(SimpleNamespace(user=viewer), None) is False
    assert perm.has_permission(SimpleNamespace(user=editor), None) is True
    assert perm.has_permission(SimpleNamespace(user=admin), None) is True


@pytest.mark.django_db
def test_is_admin_denies_editor_and_viewer_allows_admin():
    perm = IsAdmin()
    viewer = make_user(User.Role.VIEWER)
    editor = make_user(User.Role.EDITOR)
    admin = make_user(User.Role.ADMIN)

    assert perm.has_permission(SimpleNamespace(user=viewer), None) is False
    assert perm.has_permission(SimpleNamespace(user=editor), None) is False
    assert perm.has_permission(SimpleNamespace(user=admin), None) is True
