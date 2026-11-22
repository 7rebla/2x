"""API endpoints of the search app, mounted below /api/v1/."""

from django.urls import URLPattern, URLResolver, path

from twox.search.api import SearchView

urlpatterns: list[URLPattern | URLResolver] = [
    path("search/", SearchView.as_view(), name="search"),
]
