from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    PendingSheetAppendListView,
    QuarantineRowListView,
    SyncConflictViewSet,
    SyncRunListView,
    SyncRunTriggerView,
)

router = DefaultRouter()
router.register("sync/conflicts", SyncConflictViewSet, basename="sync-conflict")

urlpatterns = [
    path("sync/run/", SyncRunTriggerView.as_view(), name="sync-run"),
    path("sync/runs/", SyncRunListView.as_view(), name="sync-runs"),
    path("sync/quarantine/", QuarantineRowListView.as_view(), name="sync-quarantine"),
    path("sync/pending-appends/", PendingSheetAppendListView.as_view(), name="sync-pending-appends"),
] + router.urls
