"""API endpoints of the ingest app, mounted below /api/v1/."""

from django.urls import URLPattern, URLResolver, path

from twox.ingest.api import IngestJobListView, VersionIngestView

urlpatterns: list[URLPattern | URLResolver] = [
    path("ingest-jobs/", IngestJobListView.as_view(), name="ingest-jobs"),
    path(
        "document-versions/<int:version_id>/ingest/",
        VersionIngestView.as_view(),
        name="document-version-ingest",
    ),
]
