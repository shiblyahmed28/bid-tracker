from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CapabilitiesReferenceView,
    ChoiceListViewSet,
    ChoiceValueDetailView,
    ChoiceValueListCreateView,
    ChoiceValueRenameView,
    ChoiceValueReorderView,
    DeadlineReminderRuleViewSet,
    NotificationPolicyViewSet,
    SettingsClientViewSet,
    SettingsPersonViewSet,
    SettingsTeamViewSet,
    UserCapabilitiesView,
)

router = DefaultRouter()
router.register("settings/choice-lists", ChoiceListViewSet, basename="choice-list")
router.register("settings/notification-policies", NotificationPolicyViewSet, basename="notification-policy")
router.register("settings/deadline-rules", DeadlineReminderRuleViewSet, basename="deadline-rule")
router.register("settings/clients", SettingsClientViewSet, basename="settings-client")
router.register("settings/people", SettingsPersonViewSet, basename="settings-person")
router.register("settings/teams", SettingsTeamViewSet, basename="settings-team")

urlpatterns = [
    # Nested/custom choice-list routes must precede router.urls — the
    # router's own <key>/ detail route would otherwise swallow these first
    # (same lesson as bids/distinct/ vs the bids router in apps/bids/urls.py).
    path(
        "settings/choice-lists/<slug:list_key>/values/",
        ChoiceValueListCreateView.as_view(),
        name="choice-value-list",
    ),
    path(
        "settings/choice-lists/<slug:list_key>/values/<int:pk>/",
        ChoiceValueDetailView.as_view(),
        name="choice-value-detail",
    ),
    path(
        "settings/choice-lists/<slug:list_key>/values/<int:pk>/rename/",
        ChoiceValueRenameView.as_view(),
        name="choice-value-rename",
    ),
    path(
        "settings/choice-lists/<slug:list_key>/reorder/",
        ChoiceValueReorderView.as_view(),
        name="choice-value-reorder",
    ),
    path("settings/capabilities/", CapabilitiesReferenceView.as_view(), name="capabilities-reference"),
    path("settings/users/<int:user_id>/capabilities/", UserCapabilitiesView.as_view(), name="user-capabilities"),
] + router.urls
