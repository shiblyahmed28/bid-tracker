from django.urls import path
from rest_framework.routers import DefaultRouter

from .dashboard_views import (
    DashboardBgExposureView,
    DashboardBreakdownView,
    DashboardClassicView,
    DashboardDeadlinesView,
    DashboardSummaryView,
    DashboardTrendView,
)
from .views import BidViewSet

router = DefaultRouter()
router.register("bids", BidViewSet, basename="bid")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/trend/", DashboardTrendView.as_view(), name="dashboard-trend"),
    path("dashboard/breakdown/", DashboardBreakdownView.as_view(), name="dashboard-breakdown"),
    path("dashboard/deadlines/", DashboardDeadlinesView.as_view(), name="dashboard-deadlines"),
    path("dashboard/bg-exposure/", DashboardBgExposureView.as_view(), name="dashboard-bg-exposure"),
    path("dashboard/classic/", DashboardClassicView.as_view(), name="dashboard-classic"),
] + router.urls
