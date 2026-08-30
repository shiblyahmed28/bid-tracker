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
    PersonDuplicatesView,
    PersonEngagementsView,
    PersonMergeView,
    SendWelcomeEmailView,
    SettingsClientViewSet,
    SettingsPersonViewSet,
    SettingsTeamViewSet,
    UserCapabilitiesView,
    WelcomeEmailSettingsView,
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
    # Must precede router.urls — "duplicates" would otherwise be swallowed by
    # the router's settings/people/<pk>/ detail route (same lesson as
    # bids/distinct/ vs the bids router in apps/bids/urls.py).
    path("settings/people/duplicates/", PersonDuplicatesView.as_view(), name="person-duplicates"),
    path("settings/people/<int:pk>/merge/", PersonMergeView.as_view(), name="person-merge"),
    path("settings/people/<int:pk>/engagements/", PersonEngagementsView.as_view(), name="person-engagements"),
    path("settings/welcome-email/", WelcomeEmailSettingsView.as_view(), name="welcome-email-settings"),
    path(
        "settings/engagements/<int:pk>/welcome-email/",
        SendWelcomeEmailView.as_view(),
        name="send-welcome-email",
    ),
] + router.urls
