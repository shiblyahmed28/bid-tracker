from django.urls import path

from .views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationSettingsView,
    SentEmailListView,
)

urlpatterns = [
    path("notifications/settings/", NotificationSettingsView.as_view(), name="notification-settings"),
    path("notifications/mark-all-read/", NotificationMarkAllReadView.as_view(), name="notifications-mark-all-read"),
    path("notifications/sent-log/", SentEmailListView.as_view(), name="sent-email-log"),
    path("notifications/<int:pk>/read/", NotificationMarkReadView.as_view(), name="notification-read"),
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
]
