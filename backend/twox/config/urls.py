"""Root URL configuration."""

from django.urls import URLPattern, URLResolver, path

from twox.config.health import HealthView
from twox.config.selftest import SelftestView

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/selftest/", SelftestView.as_view(), name="selftest"),
]
