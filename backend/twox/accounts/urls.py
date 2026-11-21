"""API endpoints of the accounts app, mounted below /api/v1/."""

from django.urls import URLPattern, URLResolver, path

from twox.accounts.views import MeView

urlpatterns: list[URLPattern | URLResolver] = [
    path("me/", MeView.as_view(), name="me"),
]
