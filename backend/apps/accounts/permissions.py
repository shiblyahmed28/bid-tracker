from rest_framework.permissions import BasePermission

from .models import User


class IsAuthenticatedViewer(BasePermission):
    """Any authenticated, active user — the floor for every role."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class IsEditorOrAbove(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role in (User.Role.ADMIN, User.Role.EDITOR)
        )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active and user.role == User.Role.ADMIN
        )
