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
from .export_views import BidExportCsvView, BidExportPdfDownloadView, BidExportPdfStatusView, BidExportPdfView
from .views import BidDistinctValuesView, BidViewSet, PersonListView

router = DefaultRouter()
router.register("bids", BidViewSet, basename="bid")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/trend/", DashboardTrendView.as_view(), name="dashboard-trend"),
    path("dashboard/breakdown/", DashboardBreakdownView.as_view(), name="dashboard-breakdown"),
    path("dashboard/deadlines/", DashboardDeadlinesView.as_view(), name="dashboard-deadlines"),
    path("dashboard/bg-exposure/", DashboardBgExposureView.as_view(), name="dashboard-bg-exposure"),
    path("dashboard/classic/", DashboardClassicView.as_view(), name="dashboard-classic"),
    path("people/", PersonListView.as_view(), name="person-list"),
    # Must precede router.urls — BidViewSet's lookup regex (`[^/.]+`) would
    # otherwise swallow "distinct"/"export" as if they were a bid id.
    path("bids/distinct/", BidDistinctValuesView.as_view(), name="bid-distinct-values"),
    path("bids/export/pdf/", BidExportPdfView.as_view(), name="bid-export-pdf"),
    path("bids/export/pdf/status/", BidExportPdfStatusView.as_view(), name="bid-export-pdf-status"),
    path("bids/export/pdf/download/", BidExportPdfDownloadView.as_view(), name="bid-export-pdf-download"),
    path("bids/export/csv/", BidExportCsvView.as_view(), name="bid-export-csv"),
] + router.urls
