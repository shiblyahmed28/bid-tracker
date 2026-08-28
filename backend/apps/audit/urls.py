from django.urls import path

from .views import AuditEntryExportView, AuditEntryListView

urlpatterns = [
    path("audit/", AuditEntryListView.as_view(), name="audit-list"),
    path("audit/export/", AuditEntryExportView.as_view(), name="audit-export"),
]
