from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    ProfileUpdateView,
    RefreshView,
    RevokeOthersView,
    SessionListView,
    SessionRevokeView,
    UserSessionsView,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/profile/", ProfileUpdateView.as_view(), name="profile"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("auth/sessions/", SessionListView.as_view(), name="sessions"),
    path("auth/sessions/revoke-others/", RevokeOthersView.as_view(), name="sessions-revoke-others"),
    path("auth/sessions/<int:pk>/revoke/", SessionRevokeView.as_view(), name="session-revoke"),
    path("users/<int:user_id>/sessions/", UserSessionsView.as_view(), name="user-sessions"),
] + router.urls
