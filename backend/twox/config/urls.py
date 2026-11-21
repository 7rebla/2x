"""Root URL configuration."""

from django.urls import URLPattern, URLResolver, path

from twox.config.health import HealthView
from twox.config.selftest import SelftestView
from twox.config.webui import web_index

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/selftest/", SelftestView.as_view(), name="selftest"),
    # Exactly "/", no catch-all: /api/... and unknown paths keep their 404.
    # The files below /static/ come from WhiteNoise, not from a URL pattern.
    path("", web_index, name="web-index"),
]
