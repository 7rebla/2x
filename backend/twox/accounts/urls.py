"""API endpoints of the accounts app, mounted below /api/v1/."""

from django.urls import URLPattern, URLResolver, path

from twox.accounts.views import AuditLogView, MeView

urlpatterns: list[URLPattern | URLResolver] = [
    path("me/", MeView.as_view(), name="me"),
    path("audit-log/", AuditLogView.as_view(), name="audit-log"),
]
