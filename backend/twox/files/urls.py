"""API endpoints of the files app, mounted below /api/v1/."""

from django.urls import URLPattern, URLResolver, path

from twox.files.views import (
    DeviceDocumentsView,
    DocumentDetailView,
    DocumentVersionDownloadView,
    DocumentVersionsView,
)

urlpatterns: list[URLPattern | URLResolver] = [
    path(
        "devices/<int:device_id>/documents/",
        DeviceDocumentsView.as_view(),
        name="device-documents",
    ),
    path("documents/<int:document_id>/", DocumentDetailView.as_view(), name="document-detail"),
    path(
        "documents/<int:document_id>/versions/",
        DocumentVersionsView.as_view(),
        name="document-versions",
    ),
    path(
        "document-versions/<int:version_id>/download/",
        DocumentVersionDownloadView.as_view(),
        name="document-version-download",
    ),
]
